import numpy as np

# 1. synthetic data (100 readings, 3 sensors)
np.random.seed(42)
sensor_data = np.random.normal(loc=50, scale=10, size=(100, 3))

# 2. Compute Rolling Statistics 
# (Mean and Std using a window of 5)
# sliding window approach
window_size = 5
rolling_means = np.array([np.mean(sensor_data[i:i+window_size], axis=0)
                          for i in range(len(sensor_data) - window_size + 1)])

# 3. Data Normalization (Z-score: (x - mean) / std)
# Calculated over the entire dataset for each sensor
mean_val = np.mean(sensor_data, axis=0)
std_val = np.std(sensor_data, axis=0)
z_scores = (sensor_data - mean_val) / std_val

# 4. flag Outliers (> 2 std)
outlier_mask = np.abs(z_scores) > 2
outliers = sensor_data[outlier_mask]

print(sensor_data.shape)
print("Z-Scores (first 5 rows):\n", z_scores[:5])
print(f"Total Outliers: {np.sum(outlier_mask)}")
print("Outlier Values:\n", outliers)
