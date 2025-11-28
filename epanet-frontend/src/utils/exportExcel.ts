/**
 * Export Excel utility for Leak Detection Results
 * Sử dụng xlsx library để export Excel chuẩn
 */
// @ts-ignore - xlsx types may not be perfect
import * as XLSX from 'xlsx';
import { Leak, LeakSummary } from '../services/leakDetection';

interface ExportData {
  leaks: Leak[];
  summary: LeakSummary | null;
  threshold: number;
  exportDate: Date;
}

/**
 * Format timestamp to readable date string
 */
const formatDate = (timestamp: number): string => {
  const date = new Date(timestamp * 1000);
  return date.toLocaleString('vi-VN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
};

/**
 * Format probability to percentage
 */
const formatProbability = (probability: number): string => {
  return `${(probability * 100).toFixed(2)}%`;
};

/**
 * Get severity level based on probability
 */
const getSeverityLevel = (probability: number): string => {
  if (probability >= 0.5) return 'Rất cao';
  if (probability >= 0.3) return 'Cao';
  if (probability >= 0.1) return 'Trung bình';
  return 'Thấp';
};

/**
 * Export leak detection results to Excel
 */
export const exportLeaksToExcel = (data: ExportData): void => {
  const { leaks, summary, threshold, exportDate } = data;

  // Create workbook
  const workbook = XLSX.utils.book_new();

  // ===== Sheet 1: Summary (Tổng quan) =====
  const summaryData = [
    ['BÁO CÁO PHÁT HIỆN RÒ RỈ NƯỚC', ''],
    ['Ngày xuất báo cáo', exportDate.toLocaleString('vi-VN')],
    ['', ''],
    ['THÔNG TIN TỔNG QUAN', ''],
    ['Tổng số records', summary?.total_records || 0],
    ['Số nodes duy nhất', summary?.total_unique_nodes || 0],
    ['Số leaks phát hiện', summary?.detected_leaks || 0],
    ['Tỷ lệ phát hiện', summary?.detection_rate ? `${(summary.detection_rate * 100).toFixed(2)}%` : '0%'],
    ['Ngưỡng phát hiện', `${(threshold * 100).toFixed(2)}%`],
    ['Xác suất trung bình', summary?.avg_probability ? formatProbability(summary.avg_probability) : '0%'],
    ['Xác suất cao nhất', summary?.max_probability ? formatProbability(summary.max_probability) : '0%'],
    ['', ''],
    ['GHI CHÚ', ''],
    ['- Báo cáo này được tạo tự động từ hệ thống phát hiện rò rỉ AI', ''],
    ['- Threshold thấp (2-10%) giúp phát hiện sớm các nguy cơ rò rỉ', ''],
    ['- Mỗi node chỉ hiển thị 1 lần (leak có xác suất cao nhất)', ''],
  ];

  const summarySheet = XLSX.utils.aoa_to_sheet(summaryData);
  
  // Set column widths
  summarySheet['!cols'] = [
    { wch: 30 }, // Column A
    { wch: 30 }  // Column B
  ];

  // Style header row
  if (summarySheet['A1']) {
    summarySheet['A1'].s = {
      font: { bold: true, sz: 14 },
      alignment: { horizontal: 'center' }
    };
    summarySheet['!merges'] = [{ s: { r: 0, c: 0 }, e: { r: 0, c: 1 } }];
  }

  // Style section headers
  ['A4', 'A13'].forEach(cell => {
    if (summarySheet[cell]) {
      summarySheet[cell].s = {
        font: { bold: true, sz: 12 },
        fill: { fgColor: { rgb: 'E6F3FF' } }
      };
    }
  });

  XLSX.utils.book_append_sheet(workbook, summarySheet, 'Tổng quan');

  // ===== Sheet 2: Leaks Detail (Chi tiết leaks) =====
  if (leaks.length > 0) {
    const leaksData = [
      // Header row
      [
        'STT',
        'Node ID',
        'Xác suất rò rỉ',
        'Mức độ',
        'Thời gian phát hiện',
        'Áp lực (m)',
        'Cột nước (m)',
        'Nhu cầu (m³/s)',
        'Lưu lượng (L/s)'
      ],
      // Data rows
      ...leaks.map((leak, index) => [
        index + 1,
        leak.node_id,
        formatProbability(leak.probability),
        getSeverityLevel(leak.probability),
        formatDate(leak.timestamp),
        leak.pressure.toFixed(2),
        leak.head.toFixed(2),
        leak.demand.toFixed(6),
        (leak.flow !== undefined ? leak.flow : leak.demand * 1000).toFixed(2)
      ])
    ];

    const leaksSheet = XLSX.utils.aoa_to_sheet(leaksData);
    
    // Set column widths
    leaksSheet['!cols'] = [
      { wch: 6 },   // STT
      { wch: 12 }, // Node ID
      { wch: 15 }, // Xác suất
      { wch: 12 }, // Mức độ
      { wch: 20 }, // Thời gian
      { wch: 12 }, // Áp lực
      { wch: 12 }, // Cột nước
      { wch: 15 }, // Nhu cầu
      { wch: 15 }  // Lưu lượng
    ];

    // Style header row
    const headerRange = XLSX.utils.decode_range(leaksSheet['!ref'] || 'A1:I1');
    for (let col = headerRange.s.c; col <= headerRange.e.c; col++) {
      const cellAddress = XLSX.utils.encode_cell({ r: 0, c: col });
      if (leaksSheet[cellAddress]) {
        leaksSheet[cellAddress].s = {
          font: { bold: true, color: { rgb: 'FFFFFF' } },
          fill: { fgColor: { rgb: '4472C4' } },
          alignment: { horizontal: 'center', vertical: 'center' }
        };
      }
    }

    // Style data rows - color based on severity
    for (let row = 1; row <= leaks.length; row++) {
      const probability = leaks[row - 1].probability;
      let bgColor = 'FFFFFF'; // White (Low)
      
      if (probability >= 0.5) {
        bgColor = 'FFE6E6'; // Light red (Very High)
      } else if (probability >= 0.3) {
        bgColor = 'FFE6CC'; // Light orange (High)
      } else if (probability >= 0.1) {
        bgColor = 'FFF4CC'; // Light yellow (Medium)
      }

      for (let col = 0; col <= 8; col++) {
        const cellAddress = XLSX.utils.encode_cell({ r: row, c: col });
        if (leaksSheet[cellAddress]) {
          leaksSheet[cellAddress].s = {
            fill: { fgColor: { rgb: bgColor } },
            alignment: { horizontal: col === 0 ? 'center' : 'left', vertical: 'center' }
          };
        }
      }
    }

    // Freeze header row
    leaksSheet['!freeze'] = { xSplit: 0, ySplit: 1 };

    XLSX.utils.book_append_sheet(workbook, leaksSheet, 'Chi tiết leaks');
  }

  // ===== Sheet 3: Statistics (Thống kê) =====
  if (leaks.length > 0) {
    // Group by severity
    const severityCounts = {
      'Rất cao': leaks.filter(l => l.probability >= 0.5).length,
      'Cao': leaks.filter(l => l.probability >= 0.3 && l.probability < 0.5).length,
      'Trung bình': leaks.filter(l => l.probability >= 0.1 && l.probability < 0.3).length,
      'Thấp': leaks.filter(l => l.probability < 0.1).length
    };

    const statsData = [
      ['THỐNG KÊ THEO MỨC ĐỘ', ''],
      ['', ''],
      ['Mức độ', 'Số lượng', 'Tỷ lệ'],
      ['Rất cao (≥50%)', severityCounts['Rất cao'], `${((severityCounts['Rất cao'] / leaks.length) * 100).toFixed(2)}%`],
      ['Cao (30-50%)', severityCounts['Cao'], `${((severityCounts['Cao'] / leaks.length) * 100).toFixed(2)}%`],
      ['Trung bình (10-30%)', severityCounts['Trung bình'], `${((severityCounts['Trung bình'] / leaks.length) * 100).toFixed(2)}%`],
      ['Thấp (<10%)', severityCounts['Thấp'], `${((severityCounts['Thấp'] / leaks.length) * 100).toFixed(2)}%`],
      ['', ''],
      ['TỔNG CỘNG', leaks.length, '100%']
    ];

    const statsSheet = XLSX.utils.aoa_to_sheet(statsData);
    
    // Set column widths
    statsSheet['!cols'] = [
      { wch: 25 },
      { wch: 12 },
      { wch: 12 }
    ];

    // Style header
    if (statsSheet['A1']) {
      statsSheet['A1'].s = {
        font: { bold: true, sz: 14 },
        alignment: { horizontal: 'center' }
      };
      statsSheet['!merges'] = [{ s: { r: 0, c: 0 }, e: { r: 0, c: 2 } }];
    }

    // Style table header
    ['A3', 'B3', 'C3'].forEach(cell => {
      if (statsSheet[cell]) {
        statsSheet[cell].s = {
          font: { bold: true },
          fill: { fgColor: { rgb: 'D9E1F2' } },
          alignment: { horizontal: 'center' }
        };
      }
    });

    // Style total row
    ['A9', 'B9', 'C9'].forEach(cell => {
      if (statsSheet[cell]) {
        statsSheet[cell].s = {
          font: { bold: true },
          fill: { fgColor: { rgb: 'E6F3FF' } }
        };
      }
    });

    XLSX.utils.book_append_sheet(workbook, statsSheet, 'Thống kê');
  }

  // Generate filename with timestamp
  const timestamp = exportDate.toISOString().replace(/[:.]/g, '-').slice(0, -5);
  const filename = `Bao_Cao_Ro_Ri_${timestamp}.xlsx`;

  // Write file
  try {
    XLSX.writeFile(workbook, filename);
    console.log(`✅ Excel file exported: ${filename}`);
  } catch (error) {
    console.error('❌ Error exporting Excel:', error);
    throw new Error('Không thể xuất file Excel. Vui lòng thử lại.');
  }
};

