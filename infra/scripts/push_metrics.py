import os
import sys
import time
import random
import boto3
from dotenv import load_dotenv

load_dotenv()

REGION = os.getenv("AWS_REGION", "us-east-1")
NAMESPACE = os.getenv("CLOUDWATCH_NAMESPACE", "CAQI/PaymentMetrics")

def push_test_metrics(auth_p99: float, violation_rate: float, throughput_reward: float):
    """Pushes simulated or live CAQI telemetry to AWS CloudWatch."""
    try:
        cw = boto3.client("cloudwatch", region_name=REGION)
        cw.put_metric_data(
            Namespace=NAMESPACE,
            MetricData=[
                {
                    "MetricName": "AuthP99LatencyMs",
                    "Value": auth_p99,
                    "Unit": "Milliseconds",
                    "StorageResolution": 60
                },
                {
                    "MetricName": "ConstraintViolationRate",
                    "Value": violation_rate,
                    "Unit": "Percent",
                    "StorageResolution": 60
                },
                {
                    "MetricName": "ThroughputReward",
                    "Value": throughput_reward,
                    "Unit": "None",
                    "StorageResolution": 60
                }
            ]
        )
        print(f"[CloudWatch] Pushed telemetry: AuthP99={auth_p99:.2f}ms, ViolationRate={violation_rate:.1f}%, Reward={throughput_reward:.2f}")
        return True
    except Exception as e:
        print(f"[CloudWatch Error]: {e}")
        return False

if __name__ == "__main__":
    # Standard test run pushing 3 sample datapoints
    print("Testing boto3 CloudWatch metric integration...")
    p99_val = float(sys.argv[1]) if len(sys.argv) > 1 else 11.5 # triggers alarm default
    push_test_metrics(auth_p99=p99_val, violation_rate=5.0, throughput_reward=0.85)

