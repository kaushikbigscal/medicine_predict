import subprocess
import time
import os
import schedule
import logging
import threading

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')
file_path = './Doctor_Data.csv'

# for rerun api
class FlaskAppThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.api_process = None
        self.should_stop = threading.Event()

    def run(self):
        try:
            logging.info("********************** Running api.py... **********************")
            self.api_process = subprocess.Popen(["python3", "api.py"])  # Start Flask app in a subprocess
            logging.info("********************** api.py started successfully. **********************")
            self.api_process.wait()  # Wait for the Flask app subprocess to complete
        except EOFError as e:
            logging.error(f"EOFError: {e}. Stopping the Flask app thread.")
            self.should_stop.set()  # Stop the thread if EOFError occurs
        except Exception as e:
            logging.error(f"Error running api.py: {e}")

    def stop(self):
        self.should_stop.set()
        if self.api_process:
            self.api_process.terminate()  # Terminate the Flask app subprocess if it's running

# Method for add date in data base
def run_model():
    try:
        logging.info("********************** Running Collect_Data.py. *****************************")
        subprocess.run(["python3", "collect_data.py"])
        logging.info("********************** Collect_Data.py executed successfully. **********************")
        if os.path.exists(file_path):
            # Delete the file
            os.remove(file_path)
        # Stop and restart the Flask app after Collect_Data.py completes
        restart_api(api_thread)
    except Exception as e:
        logging.error(f"Error running Collect_Data.py: {e}")

# Method for restart api
def restart_api(api_thread):
    try:
        logging.info("********************** Restarting Flask app. **********************")
        api_thread.stop()  # Stop the current Flask app thread
        api_thread.join()  # Wait for the thread to terminate
        api_thread = FlaskAppThread()  # Create a new Flask app thread
        api_thread.start()  # Start the new Flask app thread
        logging.info("********************** Flask app restarted successfully. **********************")
    except Exception as e:
        logging.error(f"Error restarting Flask app: {e}")

if __name__ == "__main__":
    # Start the Flask app thread
    api_thread = FlaskAppThread()
    api_thread.start()

    # Schedule the Collect_Data script to run once every day at 09:47
    schedule.every().day.at("23:30").do(run_model)
    logging.info("Scheduled Collect_Data.py to run at 10:59 every day.")
    
    # Infinite loop to keep the script running
    while True:
        schedule.run_pending()  # Check for pending scheduled tasks
        # You can add additional logic here if needed
        time.sleep(1)  # Sleep for 1 second before checking again
