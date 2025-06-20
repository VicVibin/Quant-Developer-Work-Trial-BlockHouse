# Optimal Order Allocation with Kafka-Simulated Market Data

This repository demonstrates a real-time order allocation strategy using Level 1 (L1) market data streamed via Apache Kafka. It simulates streaming data and evaluates various execution strategies---including a custom optimizer, TWAP, VWAP, and naive best-ask---by comparing execution cost performance across these methods.

---

## 📈 Use Case

High-frequency trading systems or algorithmic execution engines often need to decide how to split a large order across multiple venues in real time. The goal is to minimize execution cost while considering liquidity constraints and execution risk.

This module:
- Simulates **real-time L1 quote data** from a CSV file using Kafka.
- Consumes these quotes and **allocates orders optimally** across available venues.
- Benchmarks the optimized strategy against **baseline strategies**: TWAP, VWAP, and naive best-ask.
- Outputs **costs, average fill prices, and savings in basis points (bps)**.

---

## 🛠️ Components

### 1. `kafka_producer.py`

This script streams historical market data into a Kafka topic in real-time pacing.

#### Key Features:
- Reads historical L1 market data from `l1_day.csv`.
- Filters a specific time window for simulation (`13:36:32` to `13:45:14` UTC).
- Publishes data to the Kafka topic `mock_l1_stream`, maintaining original time delays between messages.

#### Usage:
```bash
python kafka_producer.py

```

> ✅ Ensure Kafka is running locally with a topic named `mock_l1_stream`.


### 2\. `order_allocator.py`

This script listens to the Kafka stream and applies optimal allocation logic per tick. It evaluates cost performance across:

-   **Custom Allocator**: Minimizes execution cost using a configurable penalty function for underfills and overfills.

-   **Best Ask Baseline**: Routes full order to the venue with the best current ask price.

-   **TWAP (Time-Weighted Average Price)**.

-   **VWAP (Volume-Weighted Average Price)**.

#### Key Parameters:

-   `ORDER_SIZE`: Number of shares to buy (e.g. `5000`)

-   `λ_OVER`, `λ_UNDER`: Overfill/underfill penalty weights.

-   `θ_QUEUE`: Risk penalty for execution deviation.

#### Example Output:

```
{
  "best_parameters": {
    "lambda_over": 0.6,
    "lambda_under": 0.9,
    "theta_queue": 0.4
  },
  "optimized": {
    "total_cost": 28125.9,
    "total_cash": 28050.0,
    "shares_filled": 5000,
    "avg_fill_px": 5.61
  },
  "baselines": {
    "best_ask": {
      "total_cost": 28240.0,
      "total_cash": 28150.0,
      "avg_fill_px": 5.63
    },
    "twap": {...},
    "vwap": {...}
  },
  "savings_vs_baselines_bps": {
    "best_ask": 3.55,
    "twap": 5.21,
    "vwap": 4.13
  }
}

```

* * * * *

⚙️ Installation & Requirements
------------------------------

### Prerequisites

-   Python 3.8+

-   Kafka (running locally)

-   `l1_day.csv` with L1 quote data including:

    -   `publisher_id`

    -   `ask_px_00`

    -   `ask_sz_00`

    -   `ts_event`

### Install Python Dependencies

```
pip install pandas numpy confluent_kafka

```

* * * * *

🚀 How to Run
-------------

1.  **Start Kafka locally** with a topic named `mock_l1_stream`.

2.  **Run the Producer** to simulate live data:

    ```
    python simulate_producer.py

    ```

3.  **Run the Consumer/Allocator** to compute costs:

    ```
    python order_allocator.py

    ```

* * * * *

📊 Strategy Logic Overview
--------------------------

### Allocation Heuristic

The custom allocator minimizes total cost by:

-   Executing on one or more venues up to their available sizes.

-   Incorporating execution fees and rebates.

-   Applying penalties for deviating from order size (overfill/underfill).

-   Exhaustively evaluating all feasible allocation splits.

> ⚠️ Note: This exhaustive search is only efficient for a small number of venues.

### Baselines

-   **Best Ask**: Always chooses the lowest ask price available.

-   **TWAP**: Averages price over time intervals.

-   **VWAP**: Weights prices by available size.

* * * * *

📎 File Summary
---------------

| File | Description |
| --- | --- |
| `simulate_producer.py` | Streams historical L1 quotes into Kafka topic |
| `order_allocator.py` | Consumes Kafka stream and evaluates execution strategies |
| `l1_day.csv` | Historical quote data (must be present in project root) |

* * * * *

📘 Future Improvements
----------------------

-   Parallelized allocation using dynamic programming or heuristics for larger venue sets.

-   Support for bid-side data and order book depth.

-   Integration with real Kafka-based data pipelines.

-   Extend to handle limit and market orders with latency modeling.

* * * * *

📄 License
----------

This repository is for **research and educational purposes only**.

* * * * *

🧠 Acknowledgments
------------------

This project models real-world trading execution challenges and simulates optimal order placement across fragmented liquidity environments.

* * * * *

🔗 Related Topics
-----------------

-   Market Microstructure

-   Smart Order Routing (SOR)

-   High-Frequency Trading (HFT)

-   Execution Algorithms (TWAP, VWAP, POV, etc.)

```
