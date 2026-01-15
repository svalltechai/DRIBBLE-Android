import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, spacing, fontSize, borderRadius } from '../constants/theme';
import StatusBadge from './StatusBadge';

interface OrderItem {
  name: string;
  quantity: number;
  size: string;
  color: string;
}

interface Order {
  id: string;
  order_number: string;
  customer_name: string;
  customer_phone: string;
  status: string;
  total_amount: number;
  items: OrderItem[];
  created_at: string;
}

interface OrderCardProps {
  order: Order;
  onPress: () => void;
}

export default function OrderCard({ order, onPress }: OrderCardProps) {
  const totalItems = order.items?.reduce((sum, item) => sum + item.quantity, 0) || 0;
  
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  return (
    <TouchableOpacity style={styles.card} onPress={onPress} activeOpacity={0.7}>
      <View style={styles.header}>
        <View style={styles.orderInfo}>
          <Text style={styles.orderNumber}>#{order.order_number}</Text>
          <Text style={styles.date}>{formatDate(order.created_at)}</Text>
        </View>
        <StatusBadge status={order.status} size="sm" />
      </View>
      
      <View style={styles.customerRow}>
        <Ionicons name="person-outline" size={16} color={colors.textSecondary} />
        <Text style={styles.customerName} numberOfLines={1}>{order.customer_name}</Text>
        <Text style={styles.customerPhone}>{order.customer_phone}</Text>
      </View>
      
      <View style={styles.footer}>
        <View style={styles.itemsInfo}>
          <Ionicons name="cube-outline" size={16} color={colors.textSecondary} />
          <Text style={styles.itemsText}>{totalItems} items</Text>
        </View>
        <Text style={styles.amount}>{formatCurrency(order.total_amount)}</Text>
      </View>
      
      <View style={styles.arrowContainer}>
        <Ionicons name="chevron-forward" size={20} color={colors.textMuted} />
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    padding: spacing.md,
    marginBottom: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: spacing.sm,
  },
  orderInfo: {
    flex: 1,
  },
  orderNumber: {
    fontSize: fontSize.lg,
    fontWeight: '700',
    color: colors.text,
  },
  date: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
    marginTop: 2,
  },
  customerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.sm,
    paddingBottom: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  customerName: {
    fontSize: fontSize.md,
    color: colors.textSecondary,
    marginLeft: spacing.xs,
    flex: 1,
  },
  customerPhone: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  itemsInfo: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  itemsText: {
    fontSize: fontSize.sm,
    color: colors.textSecondary,
    marginLeft: spacing.xs,
  },
  amount: {
    fontSize: fontSize.xl,
    fontWeight: '700',
    color: colors.primary,
  },
  arrowContainer: {
    position: 'absolute',
    right: spacing.md,
    top: '50%',
    marginTop: -10,
  },
});
