/**
 * Configuration cho demand color coding
 * Có thể điều chỉnh các ngưỡng này theo yêu cầu nghiệp vụ
 */

export interface DemandThresholds {
  // Ngưỡng cao (báo động)
  criticalHigh: number;  // > 150%: Đỏ đậm - Demand quá cao, có vấn đề nghiêm trọng
  warningHigh: number;   // > 120%: Đỏ/Cam - Demand cao, cần chú ý
  
  // Ngưỡng bình thường
  normalHigh: number;    // > 80%: Xanh lá - Demand bình thường, hoạt động ổn định
  
  // Ngưỡng thấp
  normalLow: number;     // > 50%: Xanh dương - Demand thấp, có thể bình thường
  warningLow: number;    // > 0%: Xám - Demand rất thấp, có thể có vấn đề
}

// Ngưỡng mặc định (có thể điều chỉnh)
export const DEFAULT_DEMAND_THRESHOLDS: DemandThresholds = {
  criticalHigh: 1.5,  // 150% - Demand quá cao
  warningHigh: 1.2,   // 120% - Demand cao
  normalHigh: 0.8,   // 80% - Ngưỡng dưới của bình thường
  normalLow: 0.5,    // 50% - Ngưỡng dưới của thấp
  warningLow: 0.0,   // 0% - Không có demand
};

// Ý nghĩa màu sắc:
// export const DEMAND_COLOR_MEANINGS = {
//   criticalHigh: {
//     color: '#d32f2f', // Dark red
//     meaning: 'Demand quá cao (>150% base) - Có thể có vấn đề nghiêm trọng (rò rỉ lớn, sự cố)',
//     ratio: '> 1.5'
//   },
//   warningHigh: {
//     color: '#ff5722', // Red/Orange
//     meaning: 'Demand cao (>120% base) - Cần chú ý, có thể có rò rỉ nhỏ',
//     ratio: '1.2 - 1.5'
//   },
//   normal: {
//     color: '#4caf50', // Green
//     meaning: 'Demand bình thường (80-120% base) - Hoạt động ổn định',
//     ratio: '0.8 - 1.2'
//   },
//   normalLow: {
//     color: '#2196f3', // Blue
//     meaning: 'Demand thấp (50-80% base) - Có thể bình thường (giờ thấp điểm) hoặc cần kiểm tra',
//     ratio: '0.5 - 0.8'
//   },
//   warningLow: {
//     color: '#9e9e9e', // Grey
//     meaning: 'Demand rất thấp (0-50% base) - Có thể có vấn đề (van đóng, đường ống tắc)',
//     ratio: '0 - 0.5'
//   },
//   noDemand: {
//     color: '#607d8b', // Blue grey
//     meaning: 'Không có demand (0) - Có thể van đóng hoàn toàn',
//     ratio: '= 0'
//   },
//   noBaseDemand: {
//     color: '#9e9e9e', // Grey
//     meaning: 'Không thể so sánh (base demand = 0)',
//     ratio: 'N/A'
//   }
// };

