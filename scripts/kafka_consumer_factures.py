#!/usr/bin/env python3
"""
Consumer Kafka : lit le topic factures-enriched et écrit les messages dans
hdfs/streaming/<date>/factures_streaming_<timestamp>.json (pour pipeline temps réel).
"""
import os
import json
import signal
import sys
from datetime import datetime

def main():
    try:
        from kafka import KafkaConsumer
    except ImportError:
        print("kafka-python requis: pip install kafka-python", file=sys.stderr)
        sys.exit(1)

    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    topic = os.environ.get("KAFKA_TOPIC", "factures-enriched")
    base_path = os.environ.get("HDFS_STREAMING_PATH", "/data/streaming")

    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap.split(","),
        value_deserializer=lambda m: json.loads(m.decode("utf-8")) if m else None,
        auto_offset_reset="earliest",
        group_id="factures-consumer-group",
    )

    running = [True]

    def shutdown(signum, frame):
        running[0] = False

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    print(f"Consumer démarré: topic={topic}, bootstrap={bootstrap}", flush=True)
    batch = []
    batch_size = 50

    while running[0]:
        try:
            for msg in consumer:
                if not running[0]:
                    break
                if msg.value:
                    batch.append(msg.value)
                if len(batch) >= batch_size:
                    _flush_batch(batch, base_path)
                    batch = []
        except Exception as e:
            print(f"Erreur consumer: {e}", flush=True)
        if batch:
            _flush_batch(batch, base_path)
            batch = []

    consumer.close()
    print("Consumer arrêté.", flush=True)


def _flush_batch(batch: list, base_path: str) -> None:
    now = datetime.utcnow()
    date_str = now.strftime("%Y-%m-%d")
    ts = now.strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(base_path, date_str)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"factures_streaming_{ts}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(batch, f, ensure_ascii=False, indent=2)
    print(f"Écrit {len(batch)} factures -> {out_path}", flush=True)


if __name__ == "__main__":
    main()
