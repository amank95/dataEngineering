import time
import subprocess
import logging
import sys
from datetime import datetime, time as dtime

# Configure logging to show timestamps and activity
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - SCHEDULER - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('scheduler.log')
    ]
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION (IST based on user context) ---
MARKET_OPEN = dtime(9, 15)
MARKET_CLOSE = dtime(15, 30)
DAILY_JOB_TIME = dtime(16, 0)   # When to run the daily full download
INTRADAY_INTERVAL_SECONDS = 300 # Run every 5 minutes

def is_weekend(now):
    """Check if today is Saturday (5) or Sunday (6)."""
    return now.weekday() >= 5

def is_market_hours(now):
    """Check if current time is within market hours (09:15 - 15:30)."""
    current_time = now.time()
    return MARKET_OPEN <= current_time <= MARKET_CLOSE

def run_pipeline(args, job_name):
    """Executes the run_all.py script with specific arguments."""
    cmd = [sys.executable, "run_all.py"] + args
    
    logger.info(f"🚀 STARTING JOB: {job_name}")
    logger.info(f"   Command: {' '.join(cmd)}")
    
    try:
        # Use subprocess to run the other script. 
        # Check=True will raise an error if the script fails.
        subprocess.run(cmd, check=True)
        logger.info(f"✅ COMPLETED JOB: {job_name}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ FAILED JOB: {job_name} (Exit Code: {e.returncode})")
        return False
    except Exception as e:
        logger.error(f"❌ ERROR in {job_name}: {e}")
        return False

def main():
    logger.info("╔" + "═" * 50 + "╗")
    logger.info("║       STOCK MARKET PIPELINE SCHEDULER      ║")
    logger.info("╚" + "═" * 50 + "╝")
    logger.info(f"Running mode: Automatic")
    logger.info(f"Market Hours: {MARKET_OPEN} - {MARKET_CLOSE}")
    logger.info(f"Daily Run   : {DAILY_JOB_TIME}")
    logger.info(f"Weekends    : Skipped")
    logger.info("")

    last_intraday_run = None
    # Initialize with None to ensure we run if we start after 4 PM, 
    # OR set to today if we want to skip today's run if started late.
    # Assuming we want to run if it hasn't run yet today.
    last_daily_run_date = None

    while True:
        now = datetime.now()
        
        # ---------------------------
        # 1. WEEKEND CHECK
        # ---------------------------
        if is_weekend(now):
            logger.info("📅 It's the weekend. Sleeping for 1 hour...")
            time.sleep(3600) # Sleep an hour
            continue

        # ---------------------------
        # 2. INTRADAY JOB (Market Hours)
        # ---------------------------
        if is_market_hours(now):
            # Check if enough time has passed since last run
            if last_intraday_run is None or (now - last_intraday_run).total_seconds() >= INTRADAY_INTERVAL_SECONDS:
                
                # Run Intraday Pipeline
                logger.info(f"⚡ DETECTED MARKET OPEN ({now.strftime('%H:%M')}). Running Intraday sync...")
                run_pipeline(
                    args=["--intraday", "--interval", "5m", "--sync"], 
                    job_name="Intraday Update"
                )
                
                last_intraday_run = datetime.now()
            else:
                # Calculate time to sleep
                next_run = last_intraday_run.timestamp() + INTRADAY_INTERVAL_SECONDS
                sleep_seconds = max(1, int(next_run - now.timestamp()))
                # logger.info(f"Waiting {sleep_seconds}s for next intraday window...")
                time.sleep(min(60, sleep_seconds)) # Sleep up to 60s max to stay responsive
                continue

        # ---------------------------
        # 3. DAILY CLOSE JOB (After Market)
        # ---------------------------
        # Check if it's past the daily job time AND we haven't run it today yet
        elif now.time() >= DAILY_JOB_TIME:
            if last_daily_run_date != now.date():
                logger.info(f"🌙 MARKETS CLOSED ({now.strftime('%H:%M')}). Running Daily Closing sequence...")
                
                # Run Daily Pipeline + Drift Check + Sync
                success = run_pipeline(
                    args=["--sync", "--check-drift"], 
                    job_name="Daily Closing & Drift Check"
                )
                
                if success:
                    last_daily_run_date = now.date()
                    logger.info("💤 Daily job finished. Scheduler sleeping until tomorrow.")
            else:
                # Already ran today, just waiting
                # Log only once in a while to avoid clutter
                pass
        
        else:
            # It is a weekday, but BEFORE market open (e.g. 7 AM)
            # Just wait
            pass

        # Heartbeat / Loop delay
        time.sleep(60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n🛑 Scheduler stopped by user")
