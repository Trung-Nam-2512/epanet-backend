import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_parquet('dataset/scenario_00001/nodes.parquet')

print("\n" + "="*80)
print("GIẢI THÍCH CẤU TRÚC DATASET - SCENARIO 1")
print("="*80)

print("\n📊 TỔNG QUAN:")
print(f"  • Tổng records:     {len(df):,}")
print(f"  • Số timesteps:     {df['timestamp'].nunique()}")
print(f"  • Số nodes:         {df['node_id'].nunique()}")
print(f"  • Mỗi timestep:     194 nodes × 1 = 194 records")
print(f"  • Simulation time:  {df['timestamp'].max()/3600:.1f} giờ")
print(f"  • Time interval:    {(df['timestamp'].unique()[1])/60:.0f} phút")

print("\n🔄 QUY LUẬT LẶP:")
print("  Dataset được sắp xếp theo: TIMESTEP → NODES")
print("  ")
print("  ┌─ Timestep 0 (t=0s, 0h) ─────────────────┐")
print("  │  Row 2-195 (Index 0-193): 194 nodes    │ ← BẠN THẤY ROW 195 (TXU2)")
print("  └─────────────────────────────────────────┘")
print("  ┌─ Timestep 1 (t=900s, 0.25h) ────────────┐")
print("  │  Row 196-389 (Index 194-387): 194 nodes │")
print("  └─────────────────────────────────────────┘")
print("  ┌─ Timestep 2 (t=1800s, 0.5h) ────────────┐")
print("  │  Row 390-583 (Index 388-581): 194 nodes │ ← BẠN THẤY ROW 431")
print("  └─────────────────────────────────────────┘")
print("  ...")

print("\n❓ TẠI SAO 195 VÀ 431?")
print("  • Row 195: Là node CUỐI CÙNG (TXU2 - reservoir) của timestep 0")
print("  • Row 431: Là node THỨ 42 (node 1289) của timestep 2")
print("  • Khoảng cách 431-195 = 236 rows ≈ 1.2 timesteps")
print("  ")
print("  ℹ️  TXU2 xuất hiện ĐỊNH KỲ mỗi 194 rows:")
print(f"     Row 195, 389, 583, 777, 971, ... (Δ = 194)")

print("\n🏗️ CẤU TRÚC MỖI TIMESTEP:")
nodes_at_t0 = df[df['timestamp'] == 0]['node_id'].tolist()
print(f"  • Node 1:   {nodes_at_t0[0]} (junction)")
print(f"  • Node 2:   {nodes_at_t0[1]} (junction)")
print("  • ...")
print(f"  • Node 193: {nodes_at_t0[192]} (junction)")
print(f"  • Node 194: {nodes_at_t0[193]} (reservoir - TXU2) ← Luôn ở cuối!")

print("\n📈 THỐNG KÊ LEAK DEMAND:")
leak_stats = df.groupby('timestamp')['leak_demand'].agg(['sum', 'max', 'count'])
leak_stats['has_leak'] = (leak_stats['sum'] > 0).astype(int)
leak_count = leak_stats['has_leak'].sum()
print(f"  • Số timesteps có leak: {leak_count}/{len(leak_stats)}")
print(f"  • Tỷ lệ leak:           {100*leak_count/len(leak_stats):.1f}%")

if leak_count > 0:
    leak_times = leak_stats[leak_stats['has_leak'] == 1].index
    print(f"  • Leak bắt đầu:         t={leak_times[0]/3600:.2f}h")
    print(f"  • Leak kết thúc:        t={leak_times[-1]/3600:.2f}h")

print("\n" + "="*80)
print("TÓM LẠI:")
print("="*80)
print("✓ Không có 'chu kỳ lặp 195-431'")
print("✓ Dataset có cấu trúc CỐ ĐỊNH: 194 records/timestep")
print("✓ Row 195 = Cuối timestep 0")
print("✓ Row 431 = Giữa timestep 2")
print("✓ TXU2 (reservoir) xuất hiện định kỳ mỗi 194 rows")
print("="*80)

# Create visualization
fig, axes = plt.subplots(2, 2, figsize=(15, 10))

# 1. Records per timestep
timestep_counts = df.groupby('timestamp').size()
ax1 = axes[0, 0]
ax1.bar(range(len(timestep_counts[:20])), timestep_counts[:20].values, color='steelblue', alpha=0.7)
ax1.set_xlabel('Timestep Index', fontweight='bold')
ax1.set_ylabel('Number of Records', fontweight='bold')
ax1.set_title('Records per Timestep (First 20)', fontweight='bold', fontsize=12)
ax1.axhline(y=194, color='red', linestyle='--', label='Expected: 194 nodes')
ax1.legend()
ax1.grid(alpha=0.3)

# 2. Leak demand over time
leak_over_time = df.groupby('timestamp')['leak_demand'].sum()
ax2 = axes[0, 1]
ax2.plot(leak_over_time.index / 3600, leak_over_time.values, 'o-', color='crimson', linewidth=2, markersize=4)
ax2.set_xlabel('Time (hours)', fontweight='bold')
ax2.set_ylabel('Total Leak Demand (m³/s)', fontweight='bold')
ax2.set_title('Leak Demand Over Time', fontweight='bold', fontsize=12)
ax2.grid(alpha=0.3)
ax2.set_xlim(0, 24)

# 3. Dataset structure visualization
ax3 = axes[1, 0]
sample_data = []
for ts_idx in range(5):
    start = ts_idx * 194
    end = start + 194
    for node_idx in range(0, 194, 10):  # Sample every 10 nodes
        sample_data.append([ts_idx, node_idx, start + node_idx + 2])  # +2 for Excel row

sample_df = pd.DataFrame(sample_data, columns=['Timestep', 'Node_Index', 'Excel_Row'])
scatter = ax3.scatter(sample_df['Timestep'], sample_df['Node_Index'], 
                     c=sample_df['Excel_Row'], cmap='viridis', s=100, alpha=0.7)
ax3.set_xlabel('Timestep Index', fontweight='bold')
ax3.set_ylabel('Node Index (0-193)', fontweight='bold')
ax3.set_title('Dataset Structure (Color = Excel Row)', fontweight='bold', fontsize=12)
ax3.grid(alpha=0.3)
plt.colorbar(scatter, ax=ax3, label='Excel Row Number')

# 4. TXU2 positions
txu2_df = df[df['node_id'] == 'TXU2'].head(20)
ax4 = axes[1, 1]
excel_rows = (txu2_df.index + 2).tolist()
timesteps = (txu2_df['timestamp'] / 3600).tolist()
ax4.plot(timesteps, excel_rows, 'o-', color='darkgreen', linewidth=2.5, markersize=8, label='TXU2 (Reservoir)')
ax4.set_xlabel('Time (hours)', fontweight='bold')
ax4.set_ylabel('Excel Row Number', fontweight='bold')
ax4.set_title('TXU2 Positions (Định kỳ mỗi 194 rows)', fontweight='bold', fontsize=12)
ax4.grid(alpha=0.3)
ax4.legend()

# Add annotations for first 3 points
for i in range(min(3, len(excel_rows))):
    ax4.annotate(f'Row {excel_rows[i]}', 
                xy=(timesteps[i], excel_rows[i]),
                xytext=(10, 10), textcoords='offset points',
                fontsize=9, color='darkgreen',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.3),
                arrowprops=dict(arrowstyle='->', color='darkgreen'))

plt.tight_layout()
plt.savefig('dataset_structure_explanation.png', dpi=150, bbox_inches='tight')
print("\n✓ Saved visualization: dataset_structure_explanation.png")
plt.show()

