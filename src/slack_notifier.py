"""
Slack Notifier
===============
Sends formatted Slack alerts for drift detection and retraining events.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import requests

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Handles Slack webhook notifications for drift and retraining events."""
    
    def __init__(self, webhook_url: Optional[str] = None, enabled: bool = True):
        """
        Initialize Slack notifier.
        
        Args:
            webhook_url: Slack webhook URL (defaults to env var SLACK_WEBHOOK_URL)
            enabled: Whether Slack notifications are enabled
        """
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self.enabled = enabled and bool(self.webhook_url)
        
        if not self.enabled:
            logger.warning("Slack notifications disabled (no webhook URL configured)")
    
    def _send_message(self, payload: Dict[str, Any]) -> bool:
        """
        Send message to Slack webhook.
        
        Args:
            payload: Slack message payload
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            logger.debug("Slack disabled, skipping notification")
            return False
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=5
            )
            response.raise_for_status()
            logger.info("Slack notification sent successfully")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False
    
    def send_drift_alert(
        self,
        ticker: str,
        drift_results: Dict[str, Any],
        severity: str,
        affected_features: List[str]
    ) -> bool:
        """
        Send drift detection alert to Slack.
        
        Args:
            ticker: Stock ticker symbol
            drift_results: Dictionary of drift detection results
            severity: Drift severity (LOW/MEDIUM/HIGH/CRITICAL)
            affected_features: List of features with detected drift
            
        Returns:
            True if notification sent successfully
        """
        # Color coding based on severity
        color_map = {
            "LOW": "#36a64f",      # Green
            "MEDIUM": "#ff9900",   # Orange
            "HIGH": "#ff6600",     # Dark orange
            "CRITICAL": "#ff0000"  # Red
        }
        color = color_map.get(severity, "#808080")
        
        # Build feature summary
        feature_summary = "\n".join([
            f"• *{feat}*: p-value={drift_results.get(feat, {}).get('p_value', 'N/A'):.4f}"
            for feat in affected_features[:5]  # Limit to 5 features
        ])
        
        if len(affected_features) > 5:
            feature_summary += f"\n• _...and {len(affected_features) - 5} more features_"
        
        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": f"🚨 Data Drift Detected: {ticker}",
                    "text": f"*Severity:* {severity}\n*Affected Features:* {len(affected_features)}",
                    "fields": [
                        {
                            "title": "Drifted Features",
                            "value": feature_summary,
                            "short": False
                        },
                        {
                            "title": "Detection Time",
                            "value": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "short": True
                        }
                    ],
                    "footer": "Drift Detection System",
                    "ts": int(datetime.utcnow().timestamp())
                }
            ]
        }
        
        return self._send_message(payload)
    
    def send_retraining_confirmation(
        self,
        ticker: str,
        job_id: str,
        drift_severity: str,
        triggered_by: str = "auto_drift"
    ) -> bool:
        """
        Send retraining trigger confirmation to Slack.
        
        Args:
            ticker: Stock ticker symbol
            job_id: ML job ID from retraining API
            drift_severity: Severity of detected drift
            triggered_by: Who/what triggered retraining
            
        Returns:
            True if notification sent successfully
        """
        payload = {
            "attachments": [
                {
                    "color": "#2eb886",  # Green
                    "title": f"✅ Retraining Initiated: {ticker}",
                    "text": f"Model retraining has been automatically triggered due to {drift_severity} drift.",
                    "fields": [
                        {
                            "title": "Job ID",
                            "value": f"`{job_id}`",
                            "short": True
                        },
                        {
                            "title": "Triggered By",
                            "value": triggered_by,
                            "short": True
                        },
                        {
                            "title": "Timestamp",
                            "value": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "short": False
                        }
                    ],
                    "footer": "Auto-Retraining System",
                    "ts": int(datetime.utcnow().timestamp())
                }
            ]
        }
        
        return self._send_message(payload)
    
    def send_error_alert(
        self,
        ticker: str,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send error notification to Slack.
        
        Args:
            ticker: Stock ticker symbol
            error_type: Type of error (e.g., "ML_API_TIMEOUT", "DRIFT_DETECTION_FAILED")
            error_message: Detailed error message
            context: Additional context information
            
        Returns:
            True if notification sent successfully
        """
        context_str = ""
        if context:
            context_str = "\n".join([f"• {k}: {v}" for k, v in context.items()])
        
        payload = {
            "attachments": [
                {
                    "color": "#ff0000",  # Red
                    "title": f"❌ Error: {ticker}",
                    "text": f"*Error Type:* {error_type}\n*Message:* {error_message}",
                    "fields": [
                        {
                            "title": "Context",
                            "value": context_str or "No additional context",
                            "short": False
                        },
                        {
                            "title": "Timestamp",
                            "value": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "short": True
                        }
                    ],
                    "footer": "Error Monitoring System",
                    "ts": int(datetime.utcnow().timestamp())
                }
            ]
        }
        
        return self._send_message(payload)
    
    def send_approval_request(
        self,
        ticker: str,
        drift_severity: str,
        affected_features: List[str]
    ) -> bool:
        """
        Send approval request for critical ticker retraining.
        
        Args:
            ticker: Stock ticker symbol (critical ticker)
            drift_severity: Severity of detected drift
            affected_features: List of features with drift
            
        Returns:
            True if notification sent successfully
        """
        payload = {
            "text": f"@ml-team Approval Required",
            "attachments": [
                {
                    "color": "#ff9900",  # Orange
                    "title": f"⚠️ Approval Required: {ticker}",
                    "text": f"Drift detected on *critical ticker*. Manual approval required for retraining.",
                    "fields": [
                        {
                            "title": "Severity",
                            "value": drift_severity,
                            "short": True
                        },
                        {
                            "title": "Affected Features",
                            "value": str(len(affected_features)),
                            "short": True
                        },
                        {
                            "title": "Action Required",
                            "value": f"Review drift metrics and approve retraining via API:\n`POST /mlops/trigger-retrain/{ticker}`",
                            "short": False
                        }
                    ],
                    "footer": "Approval System",
                    "ts": int(datetime.utcnow().timestamp())
                }
            ]
        }
        
        return self._send_message(payload)
    
    def send_rate_limit_notification(
        self,
        ticker: str,
        last_retrain_time: datetime,
        cooldown_hours: int
    ) -> bool:
        """
        Send notification when retraining is skipped due to rate limiting.
        
        Args:
            ticker: Stock ticker symbol
            last_retrain_time: When the ticker was last retrained
            cooldown_hours: Cooldown period in hours
            
        Returns:
            True if notification sent successfully
        """
        time_since = datetime.utcnow() - last_retrain_time
        hours_remaining = cooldown_hours - (time_since.total_seconds() / 3600)
        
        payload = {
            "attachments": [
                {
                    "color": "#808080",  # Gray
                    "title": f"⏸️ Retraining Skipped: {ticker}",
                    "text": f"Drift detected, but retraining skipped due to rate limiting.",
                    "fields": [
                        {
                            "title": "Last Retrain",
                            "value": last_retrain_time.strftime("%Y-%m-%d %H:%M UTC"),
                            "short": True
                        },
                        {
                            "title": "Cooldown Remaining",
                            "value": f"{hours_remaining:.1f} hours",
                            "short": True
                        }
                    ],
                    "footer": "Rate Limiting System",
                    "ts": int(datetime.utcnow().timestamp())
                }
            ]
        }
        
        return self._send_message(payload)


# Singleton instance
_slack_notifier: Optional[SlackNotifier] = None


def get_slack_notifier() -> SlackNotifier:
    """Get or create singleton Slack notifier instance."""
    global _slack_notifier
    if _slack_notifier is None:
        _slack_notifier = SlackNotifier()
    return _slack_notifier
