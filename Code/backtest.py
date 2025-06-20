import numpy as np
import pandas as pd
from confluent_kafka import Consumer
import json
from collections import defaultdict
import time

fee = 0.00005 # Made global variable for easier twap and vwap computation, test case only has 1 venue
rebate = 0.0003

class Venue:
    """The venue class wrapper with parameters of the publisher_id"""
    def __init__(self, **kwargs):
        self.fee = fee
        self.rebate = rebate
        for key, value in kwargs.items():
            setattr(self, key, value)

def compute_twap(market_data, order_size, λo, λu, θ, interval_ms= 60):
    """Calculate Time-Weighted Average Price"""

    if not market_data:
        return 0, 0
    
    if len(market_data) == 1: 
        price = market_data[0]['px']
        size = market_data[0]['sz']   
        exe = min(order_size, size)
        cash_spent  = exe * (price + fee)
        maker_rebate = max(order_size - size, 0) * rebate
        cash_spent -= maker_rebate
        underfill = max(order_size - exe, 0)
        overfill = max(exe - order_size, 0)
        risk_pen = θ * (underfill + overfill)
        cost_pen = λu * underfill + λo * overfill
        cost = cash_spent + risk_pen + cost_pen
        return cost, price
    
    start_time = pd.to_datetime(market_data[0]["ts"])
    end_time = pd.to_datetime(market_data[-1]['ts'])

    df = pd.DataFrame(market_data)
    df = df[(df['ts'] >= start_time) & (df['ts'] <= end_time)]
    
    if len(df) == 0:
        return 0.0
    
    # Calculate time weights
    df['time_weight'] = df['ts'].diff().dt.total_seconds().fillna(0)
    df['weighted_px'] = df['px'] * df['time_weight']

    fixed_price = df['weighted_px'].sum() / df['time_weight'].sum()
    order = order_size
    total_cost = 0
    for i in range(len(market_data)):
        size = market_data[i]['sz']   
        exe = min(order, size)
        cash_spent  = exe * (fixed_price + fee)
        maker_rebate = max(order - size, 0) * rebate
        cash_spent -= maker_rebate
        underfill = max(order - exe, 0)
        overfill = max(exe - order, 0)
        risk_pen = θ * (underfill + overfill)
        cost_pen = λu * underfill + λo * overfill
        order -= exe
        total_cost += cash_spent + risk_pen + cost_pen
    return total_cost, fixed_price

def compute_vwap(market_data, order_size, λo, λu, θ):
    """Calculate Volume-Weighted Average Price"""

    if not market_data:
        return 0.0
    
    total_volume = sum(d['sz'] for d in market_data) # Sum of the order sizes
    if total_volume == 0:
        return 0.0
    
    fixed_price = sum(d['px'] * d['sz'] for d in market_data) / total_volume

    if len(market_data) == 1: #If only 1 order route, allocate all orders to the first venue
        price = market_data[0]['px']
        size = market_data[0]['sz']   

        exe = min(order_size, size)
        cash_spent  = exe * (fixed_price + fee)
        maker_rebate = max(order_size - size, 0) * rebate
        cash_spent -= maker_rebate
        underfill = max(order_size - exe, 0)
        overfill = max(exe - order_size, 0)
        risk_pen = θ * (underfill + overfill)
        cost_pen = λu * underfill + λo * overfill
        cost = cash_spent + risk_pen + cost_pen
        return cost, price
    
    order = order_size
    total_cost = 0

    for i in range(len(market_data)):
        size = market_data[i]['sz']   
        exe = min(order, size)
        cash_spent  = exe * (fixed_price + fee)
        maker_rebate = max(order - size, 0) * rebate
        cash_spent -= maker_rebate
        underfill = max(order - exe, 0)
        overfill = max(exe - order, 0)
        risk_pen = θ * (underfill + overfill)
        cost_pen = λu * underfill + λo * overfill
        order -= exe
        total_cost += cash_spent + risk_pen + cost_pen
    return total_cost, fixed_price

def allocate(order_size, venues, λ_over, λ_under, θ_queue):
    step = 100
    if len(venues) == 1:
        venue = venues[0]
        fill = min(order_size, venue.ask_size)
        cost, cash = compute_cost([fill], venues, order_size, λ_over, λ_under, θ_queue)
        return [fill], cost, cash

    splits = [[]]
    for v in range(len(venues) - 1):
        new_splits = []
        for alloc in splits:
            used = np.sum(alloc)
            max_v = min(order_size - used, venues[v].ask_size)
            for q in range(max_v):
                new_splits.append(alloc + [q])
        splits = new_splits

    best_cost = np.inf
    best_split = []
    for alloc in splits:
        if np.sum(alloc) != order_size:
            continue
        cost, cash = compute_cost(alloc, venues, order_size, λ_over, λ_under, θ_queue)
        if cost < best_cost:
            best_cost = cost
            best_split = alloc
    return best_split, best_cost, cash

def compute_cost(split, venues, order_size, λo, λu, θ):
    executed = 0
    cash_spent = 0
    for i in range(len(venues)):
        exe = min(split[i], venues[i].ask_size)
        executed += exe
        cash_spent += exe * (venues[i].ask + venues[i].fee)
        maker_rebate = max(split[i] - exe, 0) * venues[i].rebate
        cash_spent -= maker_rebate

    underfill = max(order_size - executed, 0)
    overfill = max(executed - order_size, 0)
    risk_pen = θ * (underfill + overfill)
    cost_pen = λu * underfill + λo * overfill
    return cash_spent + risk_pen + cost_pen, cash_spent

config = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'my_consumer_group',
    'auto.offset.reset': 'earliest'
}

consumer = Consumer(config)
topic = 'mock_l1_stream'
consumer.subscribe([topic])

ORDER_SIZE = 5000
λ_OVER = 0.6
λ_UNDER = 0.9
θ_QUEUE = 0.4

market_data = []
order_start_time = None
venues = {}
remaining_shares = ORDER_SIZE
actions = 0

results = {
    "best_parameters": {
        "lambda_over": λ_OVER,
        "lambda_under": λ_UNDER,
        "theta_queue": θ_QUEUE
    },
    "optimized": {
        "total_cost":0,
        "total_cash": 0,
        "shares_filled": 0,
        "avg_fill_px": 0.0
    },
    "baselines": {
        "best_ask": {"total_cost": 0 ,"total_cash": 0, "avg_fill_px": 0},
        "twap": {"total_cost": 0,"total_cash": 0, "avg_fill_px": 0},
        "vwap": {"total_cost": 0,"total_cash": 0, "avg_fill_px": 0}
    },
    "savings_vs_baselines_bps": {
        "best_ask": 0,
        "twap": 0,
        "vwap": 0
    }
}

try:
    while remaining_shares > 0:
        actions += 1
        msg = consumer.poll(1.0)
        if not msg:
            continue
        
        # print(msg.value())
        # print("\n")
        snapshot = json.loads(msg.value())
        current_time = pd.to_datetime(snapshot['ts_event'])
        if order_start_time is None:
            order_start_time = current_time

        venues[snapshot['publisher_id']] = Venue(
            id=snapshot["publisher_id"],
            ask=snapshot['ask_px_00'],
            ask_size=snapshot['ask_sz_00']
        )

        market_data.append({'id': snapshot['publisher_id'],
            'ts': current_time,
            'px': snapshot['ask_px_00'],
            'sz': snapshot['ask_sz_00']
        })
        
        """ The naive is the same as the allocator strategy if there is only 1 venue"""

        split, best_cost, cash = allocate(remaining_shares, list(venues.values()), λ_OVER, λ_UNDER, θ_QUEUE)
        results["optimized"]["total_cost"] += best_cost
        results["optimized"]["total_cash"] += cash
        results["optimized"]["shares_filled"] += int(np.sum(split))
        
        best_venue = min(venues.values(), key=lambda v: v.ask)
        naive_split, naive_cost, naive_cash = allocate(remaining_shares, [best_venue], λ_OVER, λ_UNDER, θ_QUEUE)
        results["baselines"]["best_ask"]["total_cost"] += naive_cost
        results["baselines"]["best_ask"]["total_cash"] += naive_cash

        remaining_shares -= int(np.sum(split))
        # print(f"Remaining shares: {remaining_shares}")


finally:
    consumer.close()
    results["optimized"]["total_cost"] = round(results["optimized"]["total_cost"], 2)
    results["optimized"]["total_cash"] = round(results["optimized"]["total_cash"], 2)
    results["baselines"]["best_ask"]["total_cash"] = round(results["baselines"]["best_ask"]["total_cash"], 2)
    results["baselines"]["best_ask"]["total_cost"]  = round(results["baselines"]["best_ask"]["total_cost"],2)
    results["optimized"]["avg_fill_px"] = round(results["optimized"]["total_cash"] / ORDER_SIZE, 2)
    results["baselines"]["best_ask"]["avg_fill_px"] = round(results["baselines"]["best_ask"]["total_cash"] / ORDER_SIZE , 2)


     # Use the last timestamp from market data instead of current system time
    end_time = pd.to_datetime(market_data[-1]['ts']) if market_data else pd.to_datetime('now').tz_localize('UTC')

    twap_cost, twap_avg_px = compute_twap(market_data, ORDER_SIZE, λ_OVER, λ_UNDER, θ_QUEUE)
    vwap_cost, vwap_avg_px = compute_vwap(market_data, ORDER_SIZE, λ_OVER, λ_UNDER, θ_QUEUE)



    # Update results with new calculations
    results["baselines"]["twap"]["total_cost"] = round(twap_cost,2)
    results["baselines"]["twap"]["avg_fill_px"] = round(twap_avg_px, 2)
    results["baselines"]["twap"]["total_cash"] = round(twap_avg_px * ORDER_SIZE, 2)
    
    results["baselines"]["vwap"]["total_cost"] = round(vwap_cost,2)
    results["baselines"]["vwap"]["avg_fill_px"] = round(vwap_avg_px, 2)
    results["baselines"]["vwap"]["total_cash"] = round(vwap_avg_px * ORDER_SIZE, 2)

    # Calculate savings in basis points
    for strategy in ["best_ask", "twap", "vwap"]:
        baseline_cost = results["baselines"][strategy]["total_cash"]
        optimized_cost = results["optimized"]["total_cash"]
        if baseline_cost > 0:
            savings_bps = ((baseline_cost - optimized_cost) / baseline_cost) * 10000
            results["savings_vs_baselines_bps"][strategy] = round(savings_bps, 5)

    print(json.dumps(results, indent=2))
    print(f"Total messages seen:{actions}")
