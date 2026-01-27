"""
Retraining Trigger System
==========================
Automatically triggers ML team's retraining API when drift is detected.
Includes safety features: rate limiting, approval mode, circuit breaker.
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit breaker to prevent repeated calls to failing ML API."""
    
    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 300):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: How long to wait before trying again
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.is_open = False
    
    def record_success(self):
        """Record successful API call."""
        self.failure_count = 0
        self.is_open = False
        logger.info("Circuit breaker reset after successful call")
    
    def record_failure(self):
        """Record failed API call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures. "
                f"Will retry after {self.timeout_seconds}s"
            )
    
    def can_attempt(self) -> bool:
        """Check if we can attempt API call."""
        if not self.is_open:
            return True
        
        # Check if timeout has passed
        if self.last_failure_time:
            elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
            if elapsed >= self.timeout_seconds:
                logger.info("Circuit breaker timeout expired, attempting call")
                self.is_open = False
                self.failure_count = 0
                return True
        
        logger.warning("Circuit breaker is open, skipping API call")
        return False


class RetrainingTrigger:
    """Handles automatic retraining trigger with safety features."""
    
    def __init__(
        self,
        ml_api_base_url: Optional[str] = None,
        ml_api_key: Optional[str] = None,
        timeout_seconds: int = 10,
        max_retries: int = 3,
        circuit_breaker_threshold: int = 5
    ):
        """
        Initialize retraining trigger.
        
        Args:
            ml_api_base_url: Base URL for ML team's API
            ml_api_key: API key for authentication
            timeout_seconds: Request timeout
            max_retries: Number of retries for failed requests
            circuit_breaker_threshold: Failures before circuit opens
        """
        self.ml_api_base_url = ml_api_base_url or os.getenv("ML_API_BASE_URL")
        self.ml_api_key = ml_api_key or os.getenv("ML_API_KEY")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        
        # Circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_breaker_threshold
        )
        
        # Setup session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,  # 1s, 2s, 4s
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        if not self.ml_api_base_url:
            logger.warning("ML API base URL not configured, retraining triggers disabled")
    
    def trigger_retraining(
        self,
        ticker: str,
        drift_severity: str,
        drift_results: Dict[str, Any],
        supabase_client=None
    ) -> Dict[str, Any]:
        """
        Trigger ML team's retraining API.
        
        Args:
            ticker: Stock ticker symbol
            drift_severity: Severity of detected drift
            drift_results: Full drift detection results
            supabase_client: Supabase client for logging (optional)
            
        Returns:
            Dictionary with trigger results
        """
        if not self.ml_api_base_url:
            return {
                "success": False,
                "error": "ML API not configured",
                "job_id": None
            }
        
        # Check circuit breaker
        if not self.circuit_breaker.can_attempt():
            return {
                "success": False,
                "error": "Circuit breaker is open (ML API unavailable)",
                "job_id": None
            }
        
        # Build API endpoint
        endpoint = f"{self.ml_api_base_url}/retrain/{ticker}"
        
        # Build request payload
        payload = {
            "ticker": ticker,
            "reason": "data_drift_detected",
            "drift_severity": drift_severity,
            "drift_features": list(drift_results.keys()),
            "triggered_at": datetime.utcnow().isoformat(),
            "triggered_by": "auto_drift_system"
        }
        
        # Build headers
        headers = {
            "Content-Type": "application/json"
        }
        if self.ml_api_key:
            headers["Authorization"] = f"Bearer {self.ml_api_key}"
        
        try:
            logger.info(f"Triggering retraining for {ticker} at {endpoint}")
            
            response = self.session.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout_seconds
            )
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            job_id = result.get("job_id") or result.get("id") or "unknown"
            
            # Record success
            self.circuit_breaker.record_success()
            
            logger.info(f"Retraining triggered successfully for {ticker}, job_id={job_id}")
            
            # Log to database if client provided
            if supabase_client:
                self._log_retraining_job(
                    supabase_client,
                    ticker,
                    job_id,
                    drift_severity,
                    "success",
                    result
                )
            
            return {
                "success": True,
                "job_id": job_id,
                "ml_api_response": result,
                "error": None
            }
            
        except requests.exceptions.Timeout:
            error_msg = f"ML API timeout after {self.timeout_seconds}s"
            logger.error(f"Retraining trigger failed for {ticker}: {error_msg}")
            self.circuit_breaker.record_failure()
            
            if supabase_client:
                self._log_retraining_job(
                    supabase_client,
                    ticker,
                    None,
                    drift_severity,
                    "timeout",
                    None,
                    error_msg
                )
            
            return {
                "success": False,
                "error": error_msg,
                "job_id": None
            }
            
        except requests.exceptions.RequestException as e:
            error_msg = f"ML API request failed: {str(e)}"
            logger.error(f"Retraining trigger failed for {ticker}: {error_msg}")
            self.circuit_breaker.record_failure()
            
            if supabase_client:
                self._log_retraining_job(
                    supabase_client,
                    ticker,
                    None,
                    drift_severity,
                    "failed",
                    None,
                    error_msg
                )
            
            return {
                "success": False,
                "error": error_msg,
                "job_id": None
            }
    
    def _log_retraining_job(
        self,
        supabase_client,
        ticker: str,
        job_id: Optional[str],
        drift_severity: str,
        status: str,
        ml_response: Optional[Dict],
        error_message: Optional[str] = None
    ):
        """Log retraining job to database."""
        try:
            record = {
                "ticker": ticker,
                "triggered_at": datetime.utcnow().isoformat(),
                "triggered_by": "auto_drift",
                "drift_severity": drift_severity,
                "ml_job_id": job_id,
                "ml_api_status": status,
                "ml_api_response": ml_response,
                "status": "pending" if status == "success" else "failed",
                "error_message": error_message
            }
            
            supabase_client.table("retraining_jobs").insert(record).execute()
            logger.info(f"Logged retraining job for {ticker} to database")
            
        except Exception as e:
            logger.error(f"Failed to log retraining job to database: {e}")
    
    def check_rate_limit(
        self,
        ticker: str,
        supabase_client,
        min_interval_hours: int = 6
    ) -> Dict[str, Any]:
        """
        Check if ticker is within rate limit for retraining.
        
        Args:
            ticker: Stock ticker symbol
            supabase_client: Supabase client
            min_interval_hours: Minimum hours between retraining
            
        Returns:
            Dictionary with rate limit status
        """
        try:
            # Query last retraining time from database
            response = supabase_client.table("retraining_jobs") \
                .select("triggered_at") \
                .eq("ticker", ticker) \
                .eq("status", "pending") \
                .order("triggered_at", desc=True) \
                .limit(1) \
                .execute()
            
            if not response.data:
                return {
                    "allowed": True,
                    "last_retrain_time": None,
                    "hours_since_last": None
                }
            
            last_retrain_str = response.data[0]["triggered_at"]
            last_retrain_time = datetime.fromisoformat(last_retrain_str.replace("Z", "+00:00"))
            
            hours_since = (datetime.utcnow() - last_retrain_time.replace(tzinfo=None)).total_seconds() / 3600
            
            allowed = hours_since >= min_interval_hours
            
            return {
                "allowed": allowed,
                "last_retrain_time": last_retrain_time,
                "hours_since_last": hours_since,
                "min_interval_hours": min_interval_hours
            }
            
        except Exception as e:
            logger.error(f"Failed to check rate limit for {ticker}: {e}")
            # Fail open - allow retraining if we can't check
            return {
                "allowed": True,
                "error": str(e)
            }
    
    def requires_approval(
        self,
        ticker: str,
        supabase_client
    ) -> bool:
        """
        Check if ticker requires manual approval for retraining.
        
        Args:
            ticker: Stock ticker symbol
            supabase_client: Supabase client
            
        Returns:
            True if approval required
        """
        try:
            response = supabase_client.table("ticker_config") \
                .select("requires_approval") \
                .eq("ticker", ticker) \
                .execute()
            
            if response.data:
                return response.data[0].get("requires_approval", False)
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check approval requirement for {ticker}: {e}")
            # Fail safe - require approval if we can't check
            return True


# Singleton instance
_retraining_trigger: Optional[RetrainingTrigger] = None


def get_retraining_trigger() -> RetrainingTrigger:
    """Get or create singleton retraining trigger instance."""
    global _retraining_trigger
    if _retraining_trigger is None:
        _retraining_trigger = RetrainingTrigger()
    return _retraining_trigger
