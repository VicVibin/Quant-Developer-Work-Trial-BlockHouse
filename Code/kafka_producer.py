import pandas as pd
import numpy as np
from confluent_kafka import Producer
import time
import json


configuration = {'bootstrap.servers': 'localhost:9092'}
producer =  Producer(configuration)

df  = pd.read_csv("l1_day.csv") # Reads CSV data
df["ts_event"] = pd.to_datetime(df['ts_event'])   # Converts to datetime

# Selected time window of data parsing (13:36:32 to 13:45:14 UTC)
start_time = pd.to_datetime('13:36:32').time()
end_time = pd.to_datetime('13:45:14').time()
df_filtered = df[(df['ts_event'].dt.time >= start_time) & (df['ts_event'].dt.time <= end_time)]

# --- Simulate Real-Time Streaming ---

def simulate_l1_stream():
    prev_ts = None
    print("Iterating through df_filtered")
    for _, row in df_filtered.iterrows():
        # Extract snapshot data (adjust columns as needed)
        snapshot = {
            "publisher_id": row['publisher_id'],
            "ask_px_00": row['ask_px_00'],
            "ask_sz_00": row['ask_sz_00'],
            "ts_event": str(row['ts_event'])  # Convert timestamp to string
            }

        # Simulate real-time pacing using time.sleep()
        if prev_ts is not None:
            time_delta = (row['ts_event'] - prev_ts).total_seconds()
            time.sleep(time_delta)  # Respect original timing
        
        prev_ts = row['ts_event']

        # Send to Kafka
        producer.produce(
            topic='mock_l1_stream',
            value=json.dumps(snapshot, indent = 4).encode('utf-8')
            )
        
        
        prev_ts = row['ts_event']

    producer.flush()  # Ensure message is sent


simulate_l1_stream()
