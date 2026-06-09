from dotenv import load_dotenv
load_dotenv()

from agent.scheduler import start_scheduler

if __name__ == "__main__":
    print("[main] ADO Daily Digest Agent starting...")
    start_scheduler()
