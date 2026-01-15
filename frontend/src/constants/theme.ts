// DRIBBLE Admin Theme - Simple and Clean
export const colors = {
  // Primary
  primary: '#3B82F6',
  primaryDark: '#2563EB',
  primaryLight: '#60A5FA',
  
  // Background
  background: '#0F172A',
  surface: '#1E293B',
  surfaceLight: '#334155',
  
  // Text
  text: '#F8FAFC',
  textSecondary: '#94A3B8',
  textMuted: '#64748B',
  
  // Status Colors
  success: '#10B981',
  warning: '#F59E0B',
  error: '#EF4444',
  info: '#3B82F6',
  
  // Order Status Colors
  pending: '#F59E0B',
  paymentPending: '#F97316',
  paid: '#10B981',
  confirmed: '#3B82F6',
  processing: '#8B5CF6',
  shipped: '#6366F1',
  delivered: '#059669',
  cancelled: '#EF4444',
  
  // Borders
  border: '#334155',
  borderLight: '#475569',
  
  // Other
  white: '#FFFFFF',
  black: '#000000',
  transparent: 'transparent',
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
};

export const fontSize = {
  xs: 10,
  sm: 12,
  md: 14,
  lg: 16,
  xl: 18,
  xxl: 24,
  xxxl: 32,
};

export const borderRadius = {
  sm: 4,
  md: 8,
  lg: 12,
  xl: 16,
  full: 9999,
};

export const ORDER_STATUS_CONFIG: Record<string, { label: string; color: string; bgColor: string }> = {
  pending: { label: 'Pending', color: colors.pending, bgColor: 'rgba(245, 158, 11, 0.15)' },
  payment_pending: { label: 'Payment Pending', color: colors.paymentPending, bgColor: 'rgba(249, 115, 22, 0.15)' },
  paid: { label: 'Paid', color: colors.paid, bgColor: 'rgba(16, 185, 129, 0.15)' },
  confirmed: { label: 'Confirmed', color: colors.confirmed, bgColor: 'rgba(59, 130, 246, 0.15)' },
  processing: { label: 'Processing', color: colors.processing, bgColor: 'rgba(139, 92, 246, 0.15)' },
  shipped: { label: 'Shipped', color: colors.shipped, bgColor: 'rgba(99, 102, 241, 0.15)' },
  delivered: { label: 'Delivered', color: colors.delivered, bgColor: 'rgba(5, 150, 105, 0.15)' },
  cancelled: { label: 'Cancelled', color: colors.cancelled, bgColor: 'rgba(239, 68, 68, 0.15)' },
};

export const getStatusConfig = (status: string) => {
  return ORDER_STATUS_CONFIG[status] || { label: status, color: colors.textMuted, bgColor: colors.surface };
};
