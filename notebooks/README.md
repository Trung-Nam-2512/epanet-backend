# 📓 JUPYTER NOTEBOOK - TRAINING HƯỚNG DẪN

## 📁 File

- **`train_leak_detection.ipynb`**: Notebook training mô hình phát hiện rò rỉ

## 🚀 Cách sử dụng

### Option 1: Jupyter Notebook (Khuyến nghị)

```bash
# Từ thư mục gốc C:\EPANET
jupyter notebook notebooks/train_leak_detection.ipynb
```

### Option 2: JupyterLab

```bash
# Từ thư mục gốc C:\EPANET
jupyter lab notebooks/train_leak_detection.ipynb
```

### Option 3: VS Code

1. Mở VS Code
2. File → Open → `notebooks/train_leak_detection.ipynb`
3. VS Code tự động hiển thị notebook
4. Chọn Python kernel (venv)

---

## ⚠️ LƯU Ý QUAN TRỌNG

### 1. **Đường dẫn (Path)**

Notebook đã được **tự động điều chỉnh** để chạy từ thư mục `notebooks/`:

```python
# Cell 4 tự động kiểm tra và điều chỉnh path
if os.path.basename(os.getcwd()) == 'notebooks':
    os.chdir('..')  # Đi lên thư mục gốc
```

✅ **Không cần lo lắng về path!** Notebook sẽ tự động tìm dataset.

### 2. **Memory (RAM)**

Mặc định load **500 scenarios** (~9.4M records):

```python
max_scenarios = 500  # Cell 10
```

❗ Nếu gặp **MemoryError**, giảm xuống:
- 300 scenarios (~5.6M records)
- 200 scenarios (~3.8M records)  
- 100 scenarios (~1.9M records)

### 3. **Thứ tự chạy**

Chạy **TUẦN TỰ từ Cell 0** → Cell cuối:

```
Cell 0-2:   Import libraries
Cell 3-8:   Load dataset  
Cell 9-13:  Labeling
Cell 14-20: Feature engineering
Cell 21-25: Train/Val/Test split
Cell 26-30: Training
Cell 31-40: Evaluation
Cell 41-45: Save model
```

---

## 📊 Nội dung Notebook

### 1. **Load Dataset**
- Load parquet files từ `dataset/scenario_xxxxx/nodes.parquet`
- Kiểm tra structure và columns
- Load 500 scenarios (có thể điều chỉnh)

### 2. **Labeling**
- Label = 1 khi: `(node == leak_node) AND (timestamp in [start, end])`
- Hỗ trợ multiple leaks per scenario
- So sánh old vs new labeling

### 3. **Feature Engineering**

**Temporal features:**
- `pressure_change`, `head_change`
- Moving averages: `pressure_ma3`, `pressure_ma5`, `head_ma3`, `head_ma5`
- Pressure/head drops

**Spatial features:**
- Network statistics: `network_pressure_mean`, `network_pressure_std`
- Node deviations: `pressure_deviation`, `demand_deviation`

**Total**: 16 features

### 4. **Training**

- **Model**: CatBoost Classifier
- **Split**: 70% train / 15% val / 15% test (by scenario)
- **Class weights**: Tự động tính để xử lý imbalance
- **Early stopping**: 100 rounds

### 5. **Evaluation**

**Metrics:**
- Accuracy, Precision, Recall, F1, F2, ROC-AUC
- **Top-K Accuracy**: Top-1, Top-5, Top-10 (leak localization)
- Confusion matrix
- Feature importance

---

## 🎯 Kết quả mong đợi

### ✅ **Metrics tốt:**
- **Accuracy**: >95%
- **ROC-AUC**: >80%
- **Top-5 Accuracy**: >30%

### ⚠️ **Cần cải thiện:**
- **Recall**: Thường thấp (~30-40%)
- **Top-1 Accuracy**: Khó đạt cao (~15-20%)

---

## 💡 Tips & Tricks

### 1. **Restart Kernel khi cần**

```python
# Nếu gặp lỗi kỳ lạ
# Menu → Kernel → Restart & Clear Output
```

### 2. **Thêm Visualization**

Bạn có thể thêm cells mới để vẽ charts:

```python
# Thêm cell mới sau training
import matplotlib.pyplot as plt

# Plot training history
plt.figure(figsize=(12, 4))
plt.subplot(1, 2, 1)
plt.plot(history)  # Nếu có
plt.title('Training History')
plt.show()
```

### 3. **Save checkpoint**

```python
# Thêm cell sau feature engineering
df_ml.to_parquet('checkpoint_features.parquet')
print("✅ Saved checkpoint")
```

### 4. **Interactive exploration**

```python
# Thêm cell để khám phá
df_ml.describe()
df_ml.info()
df_ml.groupby('has_leak').size()
```

---

## 🐛 Troubleshooting

### ❌ **"IndexError: list index out of range"**

**Nguyên nhân**: Không tìm thấy dataset

**Giải pháp**:
1. Kiểm tra thư mục: `ls dataset/` hoặc `dir dataset\`
2. Đảm bảo đã chạy: `python scripts/generate_leak_scenarios.py`
3. Restart kernel và chạy lại từ đầu

### ❌ **"MemoryError"**

**Giải pháp**:
1. Giảm `max_scenarios` trong Cell 10 (từ 500 → 300 → 200)
2. Close các ứng dụng khác
3. Restart kernel để giải phóng RAM

### ❌ **"CatBoost not installed"**

**Giải pháp**:
```bash
pip install catboost
```

### ❌ **"FileNotFoundError: metadata.csv"**

**Giải pháp**:
- Đảm bảo file `dataset/metadata.csv` tồn tại
- Chạy lại generate_leak_scenarios.py để tạo metadata

---

## 📝 Chỉnh sửa Notebook

### Thêm cell mới

1. Click vào cell muốn thêm phía sau
2. Nhấn `B` (below) hoặc `A` (above)
3. Chuyển sang Code/Markdown: `M` (markdown) hoặc `Y` (code)

### Shortcuts hữu ích

| Shortcut | Chức năng |
|----------|-----------|
| `Shift + Enter` | Chạy cell và xuống cell tiếp |
| `Ctrl + Enter` | Chạy cell (không di chuyển) |
| `A` | Thêm cell phía trên |
| `B` | Thêm cell phía dưới |
| `DD` | Xóa cell |
| `M` | Chuyển sang Markdown |
| `Y` | Chuyển sang Code |
| `Ctrl + S` | Save notebook |

---

## 🎓 Học thêm

- [Jupyter Notebook Documentation](https://jupyter-notebook.readthedocs.io/)
- [CatBoost Documentation](https://catboost.ai/docs/)
- [Pandas Documentation](https://pandas.pydata.org/docs/)

---

**Tạo bởi**: Leak Detection System  
**Cập nhật**: 2025-11-02  
**Version**: 1.0







