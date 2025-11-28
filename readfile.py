import pandas as pd
import csv

# Đọc metadata
with open("dataset/metadata.csv", 'r') as f:
    reader = csv.DictReader(f)
    scenarios = {int(row['scenario_id']): row for row in reader}

df1 = pd.read_parquet("dataset/scenario_00001.parquet")
df2 = pd.read_parquet("dataset/scenario_00002.parquet")

print("="*80)
print("SCENARIO 1 ANALYSIS")
print("="*80)
print(f"Shape: {df1.shape}")

s1 = scenarios[1]
leak_node = str(s1['leak_node'])
leak_node_norm = str(int(float(leak_node))) if '.' in leak_node else leak_node
start_s = float(s1['start_time_s'])
end_s = float(s1['end_time_s'])

print(f"\nMetadata:")
print(f"  leak_node: {leak_node} -> '{leak_node_norm}'")
print(f"  leak_time: [{start_s}s, {end_s}s]")

# Tìm records tại leak node
df1['node_id_str'] = df1['node_id'].astype(str)
leak_records = df1[df1['node_id_str'] == leak_node_norm]
print(f"\nRecords at leak node '{leak_node_norm}': {len(leak_records)}")

# Records trong leak time
leak_time_records = leak_records[
    (leak_records['timestamp'] >= start_s) &
    (leak_records['timestamp'] <= end_s)
]

print(f"Records IN leak time [{start_s}s, {end_s}s]: {len(leak_time_records)}")

if len(leak_time_records) > 0:
    print(f"\n*** RECORDS IN LEAK TIME (first 10): ***")
    print(leak_time_records[['timestamp', 'node_id_str', 'pressure', 'leak_demand']].head(10))
    
    non_zero = leak_time_records[leak_time_records['leak_demand'] > 0]
    print(f"\nRecords with leak_demand > 0: {len(non_zero)}/{len(leak_time_records)}")
    if len(non_zero) > 0:
        print(f"Max leak_demand: {non_zero['leak_demand'].max():.6f} L/s")
        print(f"Min leak_demand: {non_zero['leak_demand'].min():.6f} L/s")
    else:
        print("\n*** PROBLEM: leak_demand = 0 in leak time! ***")
else:
    print("\n*** NO RECORDS IN LEAK TIME! ***")

print("\n" + "="*80)
print("NOTE: Records with timestamp=0 are OUTSIDE leak time range")
print("You need to check records IN leak time range to see leak_demand > 0")
print("="*80)

print("\n" + "="*80)
print("SCENARIO 2 ANALYSIS")
print("="*80)

s2 = scenarios[2]
leak_node2 = str(s2['leak_node'])
leak_node_norm2 = str(int(float(leak_node2))) if '.' in leak_node2 else leak_node2
start_s2 = float(s2['start_time_s'])
end_s2 = float(s2['end_time_s'])

print(f"leak_node: {leak_node2} -> '{leak_node_norm2}'")
print(f"leak_time: [{start_s2}s, {end_s2}s]")

df2['node_id_str'] = df2['node_id'].astype(str)
leak_records2 = df2[df2['node_id_str'] == leak_node_norm2]
leak_time_records2 = leak_records2[
    (leak_records2['timestamp'] >= start_s2) &
    (leak_records2['timestamp'] <= end_s2)
]

print(f"Records IN leak time: {len(leak_time_records2)}")
if len(leak_time_records2) > 0:
    non_zero2 = leak_time_records2[leak_time_records2['leak_demand'] > 0]
    print(f"Records with leak_demand > 0: {len(non_zero2)}/{len(leak_time_records2)}")
    if len(non_zero2) > 0:
        print(f"Max: {non_zero2['leak_demand'].max():.6f} L/s")
        print("\nSample records:")
        print(non_zero2[['timestamp', 'node_id_str', 'pressure', 'leak_demand']].head(5))

print("\nSố node khác nhau trong scenario 1:", df1["node_id"].nunique())
print("Số timestamp khác nhau:", df1["timestamp"].nunique())
