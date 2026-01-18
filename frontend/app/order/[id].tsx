import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  Alert,
  Linking,
} from 'react-native';
import { Stack, useLocalSearchParams, router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { ordersAPI } from '../../src/services/api';
import { colors, spacing, fontSize, borderRadius, getStatusConfig } from '../../src/constants/theme';
import StatusBadge from '../../src/components/StatusBadge';
import LoadingSpinner from '../../src/components/LoadingSpinner';

const STATUS_FLOW = ['pending', 'payment_pending', 'paid', 'confirmed', 'processing', 'shipped', 'delivered'];

export default function OrderDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [order, setOrder] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);

  useEffect(() => {
    fetchOrder();
  }, [id]);

  const fetchOrder = async () => {
    try {
      setIsLoading(true);
      const data = await ordersAPI.getOrder(id as string);
      setOrder(data);
    } catch (error: any) {
      console.error('Error fetching order:', error);
      Alert.alert('Error', 'Failed to load order details');
    } finally {
      setIsLoading(false);
    }
  };

  const getNextStatus = (currentStatus: string): string | null => {
    const currentIndex = STATUS_FLOW.indexOf(currentStatus);
    if (currentIndex === -1 || currentIndex >= STATUS_FLOW.length - 1) {
      return null;
    }
    // Skip payment_pending when advancing from pending
    if (currentStatus === 'pending') {
      return 'confirmed';
    }
    if (currentStatus === 'paid') {
      return 'confirmed';
    }
    return STATUS_FLOW[currentIndex + 1];
  };

  const handleUpdateStatus = async (newStatus: string) => {
    const statusConfig = getStatusConfig(newStatus);
    
    Alert.alert(
      'Update Status',
      `Change order status to "${statusConfig.label}"?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Confirm',
          onPress: async () => {
            try {
              setIsUpdating(true);
              await ordersAPI.updateOrderStatus(id as string, newStatus);
              await fetchOrder();
              Alert.alert('Success', `Order status updated to ${statusConfig.label}`);
            } catch (error: any) {
              console.error('Error updating status:', error);
              Alert.alert('Error', error.response?.data?.detail || 'Failed to update status');
            } finally {
              setIsUpdating(false);
            }
          },
        },
      ]
    );
  };

  const handleCancelOrder = () => {
    Alert.alert(
      'Cancel Order',
      'Are you sure you want to cancel this order? This action cannot be undone.',
      [
        { text: 'No', style: 'cancel' },
        {
          text: 'Yes, Cancel',
          style: 'destructive',
          onPress: async () => {
            try {
              setIsUpdating(true);
              // Use the new cancel order endpoint (synced with DRIBBLE-NEW-2026)
              await ordersAPI.cancelOrder(id as string, 'Cancelled by admin from mobile app');
              await fetchOrder();
              Alert.alert('Order Cancelled', 'The order has been cancelled successfully.');
            } catch (error: any) {
              console.error('Error cancelling order:', error);
              Alert.alert('Error', error.response?.data?.detail || 'Failed to cancel order');
            } finally {
              setIsUpdating(false);
            }
          },
        },
      ]
    );
  };

  const handleCallCustomer = () => {
    if (order?.customer_phone) {
      Linking.openURL(`tel:${order.customer_phone}`);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
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

  if (isLoading) {
    return <LoadingSpinner fullScreen message="Loading order..." />;
  }

  if (!order) {
    return (
      <View style={styles.errorContainer}>
        <Ionicons name="alert-circle-outline" size={64} color={colors.error} />
        <Text style={styles.errorText}>Order not found</Text>
        <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
          <Text style={styles.backButtonText}>Go Back</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const nextStatus = getNextStatus(order.status);
  const canCancel = !['cancelled', 'delivered', 'shipped'].includes(order.status);

  return (
    <View style={styles.container}>
      <Stack.Screen
        options={{
          title: `#${order.order_number}`,
          headerBackTitle: 'Orders',
        }}
      />

      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        {/* Status Section */}
        <View style={styles.section}>
          <View style={styles.statusHeader}>
            <StatusBadge status={order.status} />
            <Text style={styles.orderDate}>{formatDate(order.created_at)}</Text>
          </View>
        </View>

        {/* Customer Info */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Customer</Text>
          <View style={styles.card}>
            <View style={styles.customerRow}>
              <View style={styles.customerInfo}>
                <Text style={styles.customerName}>{order.customer_name}</Text>
                <Text style={styles.customerPhone}>{order.customer_phone}</Text>
                <Text style={styles.customerEmail}>{order.customer_email}</Text>
              </View>
              <TouchableOpacity style={styles.callButton} onPress={handleCallCustomer}>
                <Ionicons name="call" size={20} color={colors.white} />
              </TouchableOpacity>
            </View>
          </View>
        </View>

        {/* Shipping Address */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Shipping Address</Text>
          <View style={styles.card}>
            <Text style={styles.addressName}>{order.shipping_address?.person_name}</Text>
            {order.shipping_address?.business_name && (
              <Text style={styles.addressBusiness}>{order.shipping_address.business_name}</Text>
            )}
            <Text style={styles.addressText}>{order.shipping_address?.address}</Text>
            <Text style={styles.addressText}>
              {order.shipping_address?.city}, {order.shipping_address?.state} - {order.shipping_address?.pincode}
            </Text>
            <Text style={styles.addressPhone}>📞 {order.shipping_address?.mobile_1}</Text>
            {order.shipping_address?.gst_number && (
              <Text style={styles.gstNumber}>GST: {order.shipping_address.gst_number}</Text>
            )}
          </View>
        </View>

        {/* Order Items */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Items ({order.items?.length || 0})</Text>
          <View style={styles.card}>
            {order.items?.map((item: any, index: number) => (
              <View
                key={index}
                style={[
                  styles.itemRow,
                  index < order.items.length - 1 && styles.itemRowBorder,
                ]}
              >
                <View style={styles.itemInfo}>
                  <Text style={styles.itemName}>{item.name}</Text>
                  <Text style={styles.itemVariant}>
                    {item.color} / {item.size} • Qty: {item.quantity}
                  </Text>
                </View>
                <Text style={styles.itemPrice}>{formatCurrency(item.price * item.quantity)}</Text>
              </View>
            ))}
          </View>
        </View>

        {/* Order Summary */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Summary</Text>
          <View style={styles.card}>
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>Subtotal</Text>
              <Text style={styles.summaryValue}>{formatCurrency(order.subtotal)}</Text>
            </View>
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>Tax (GST)</Text>
              <Text style={styles.summaryValue}>{formatCurrency(order.tax)}</Text>
            </View>
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>Shipping</Text>
              <Text style={styles.summaryValue}>{formatCurrency(order.shipping_cost || 0)}</Text>
            </View>
            <View style={[styles.summaryRow, styles.totalRow]}>
              <Text style={styles.totalLabel}>Total</Text>
              <Text style={styles.totalValue}>{formatCurrency(order.total_amount)}</Text>
            </View>
          </View>
        </View>

        {/* Payment Info */}
        {order.razorpay_payment_id && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Payment</Text>
            <View style={styles.card}>
              <View style={styles.paymentRow}>
                <Text style={styles.paymentLabel}>Payment ID</Text>
                <Text style={styles.paymentValue}>{order.razorpay_payment_id}</Text>
              </View>
              {order.payment_method && (
                <View style={[styles.paymentRow, { marginTop: spacing.xs }]}>
                  <Text style={styles.paymentLabel}>Method</Text>
                  <Text style={styles.paymentValue}>{order.payment_method}</Text>
                </View>
              )}
              {order.payment_gateway && (
                <View style={[styles.paymentRow, { marginTop: spacing.xs }]}>
                  <Text style={styles.paymentLabel}>Gateway</Text>
                  <Text style={styles.paymentValue}>{order.payment_gateway}</Text>
                </View>
              )}
            </View>
          </View>
        )}

        {/* Shipment Tracking - New from DRIBBLE-NEW-2026 */}
        {order.shipment && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Shipment</Text>
            <View style={styles.card}>
              {order.shipment.awb_number && (
                <View style={styles.paymentRow}>
                  <Text style={styles.paymentLabel}>AWB Number</Text>
                  <Text style={[styles.paymentValue, { fontFamily: 'monospace' }]}>{order.shipment.awb_number}</Text>
                </View>
              )}
              {order.shipment.carrier_name && (
                <View style={[styles.paymentRow, { marginTop: spacing.xs }]}>
                  <Text style={styles.paymentLabel}>Carrier</Text>
                  <Text style={styles.paymentValue}>{order.shipment.carrier_name} ({order.shipment.carrier_mode || 'Standard'})</Text>
                </View>
              )}
              {order.shipment.estimated_days && (
                <View style={[styles.paymentRow, { marginTop: spacing.xs }]}>
                  <Text style={styles.paymentLabel}>Est. Delivery</Text>
                  <Text style={styles.paymentValue}>{order.shipment.estimated_days}</Text>
                </View>
              )}
              {order.shipment.status && (
                <View style={[styles.paymentRow, { marginTop: spacing.xs }]}>
                  <Text style={styles.paymentLabel}>Status</Text>
                  <Text style={[styles.paymentValue, { textTransform: 'capitalize' }]}>{order.shipment.status}</Text>
                </View>
              )}
            </View>
          </View>
        )}

        {/* Selected Courier - New from DRIBBLE-NEW-2026 */}
        {order.selected_courier && !order.shipment && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Selected Courier</Text>
            <View style={styles.card}>
              <View style={styles.paymentRow}>
                <Text style={styles.paymentLabel}>Courier</Text>
                <Text style={styles.paymentValue}>{order.selected_courier.full_name || order.selected_courier.name}</Text>
              </View>
              {order.selected_courier.mode && (
                <View style={[styles.paymentRow, { marginTop: spacing.xs }]}>
                  <Text style={styles.paymentLabel}>Mode</Text>
                  <Text style={styles.paymentValue}>{order.selected_courier.mode}</Text>
                </View>
              )}
              {order.selected_courier.estimated_days && (
                <View style={[styles.paymentRow, { marginTop: spacing.xs }]}>
                  <Text style={styles.paymentLabel}>Est. Delivery</Text>
                  <Text style={styles.paymentValue}>{order.selected_courier.estimated_days}</Text>
                </View>
              )}
              {order.selected_courier.rate > 0 && (
                <View style={[styles.paymentRow, { marginTop: spacing.xs }]}>
                  <Text style={styles.paymentLabel}>Shipping Rate</Text>
                  <Text style={styles.paymentValue}>{formatCurrency(order.selected_courier.rate)}</Text>
                </View>
              )}
            </View>
          </View>
        )}

        {/* Order Notes */}
        {order.order_notes && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Notes</Text>
            <View style={styles.card}>
              <Text style={styles.notesText}>{order.order_notes}</Text>
            </View>
          </View>
        )}

        {/* Spacer for action buttons */}
        <View style={{ height: 120 }} />
      </ScrollView>

      {/* Action Buttons */}
      {order.status !== 'cancelled' && order.status !== 'delivered' && (
        <View style={styles.actionContainer}>
          {canCancel && (
            <TouchableOpacity
              style={styles.cancelButton}
              onPress={handleCancelOrder}
              disabled={isUpdating}
            >
              <Ionicons name="close-circle-outline" size={20} color={colors.error} />
              <Text style={styles.cancelButtonText}>Cancel</Text>
            </TouchableOpacity>
          )}
          
          {nextStatus && (
            <TouchableOpacity
              style={[styles.advanceButton, isUpdating && styles.buttonDisabled]}
              onPress={() => handleUpdateStatus(nextStatus)}
              disabled={isUpdating}
            >
              {isUpdating ? (
                <LoadingSpinner />
              ) : (
                <>
                  <Text style={styles.advanceButtonText}>
                    Mark as {getStatusConfig(nextStatus).label}
                  </Text>
                  <Ionicons name="arrow-forward" size={20} color={colors.white} />
                </>
              )}
            </TouchableOpacity>
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  scrollView: {
    flex: 1,
  },
  section: {
    paddingHorizontal: spacing.md,
    marginTop: spacing.md,
  },
  sectionTitle: {
    fontSize: fontSize.sm,
    fontWeight: '600',
    color: colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: spacing.sm,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.lg,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  statusHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  orderDate: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
  },
  customerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  customerInfo: {
    flex: 1,
  },
  customerName: {
    fontSize: fontSize.lg,
    fontWeight: '600',
    color: colors.text,
  },
  customerPhone: {
    fontSize: fontSize.md,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
  customerEmail: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    marginTop: spacing.xs,
  },
  callButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.success,
    alignItems: 'center',
    justifyContent: 'center',
  },
  addressName: {
    fontSize: fontSize.md,
    fontWeight: '600',
    color: colors.text,
  },
  addressBusiness: {
    fontSize: fontSize.sm,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
  addressText: {
    fontSize: fontSize.sm,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
  addressPhone: {
    fontSize: fontSize.sm,
    color: colors.textSecondary,
    marginTop: spacing.sm,
  },
  gstNumber: {
    fontSize: fontSize.sm,
    color: colors.primary,
    marginTop: spacing.xs,
  },
  itemRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.sm,
  },
  itemRowBorder: {
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  itemInfo: {
    flex: 1,
  },
  itemName: {
    fontSize: fontSize.md,
    fontWeight: '500',
    color: colors.text,
  },
  itemVariant: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    marginTop: spacing.xs,
  },
  itemPrice: {
    fontSize: fontSize.md,
    fontWeight: '600',
    color: colors.text,
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: spacing.xs,
  },
  summaryLabel: {
    fontSize: fontSize.md,
    color: colors.textSecondary,
  },
  summaryValue: {
    fontSize: fontSize.md,
    color: colors.text,
  },
  totalRow: {
    borderTopWidth: 1,
    borderTopColor: colors.border,
    marginTop: spacing.sm,
    paddingTop: spacing.sm,
  },
  totalLabel: {
    fontSize: fontSize.lg,
    fontWeight: '700',
    color: colors.text,
  },
  totalValue: {
    fontSize: fontSize.xl,
    fontWeight: '700',
    color: colors.primary,
  },
  paymentRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  paymentLabel: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
  },
  paymentValue: {
    fontSize: fontSize.sm,
    color: colors.text,
    fontFamily: 'monospace',
  },
  notesText: {
    fontSize: fontSize.md,
    color: colors.textSecondary,
    lineHeight: 22,
  },
  actionContainer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    padding: spacing.md,
    paddingBottom: spacing.lg,
    backgroundColor: colors.background,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    gap: spacing.sm,
  },
  cancelButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    borderRadius: borderRadius.lg,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.error,
    gap: spacing.xs,
  },
  cancelButtonText: {
    fontSize: fontSize.md,
    fontWeight: '600',
    color: colors.error,
  },
  advanceButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.md,
    borderRadius: borderRadius.lg,
    backgroundColor: colors.primary,
    gap: spacing.sm,
  },
  advanceButtonText: {
    fontSize: fontSize.md,
    fontWeight: '600',
    color: colors.white,
  },
  buttonDisabled: {
    opacity: 0.7,
  },
  errorContainer: {
    flex: 1,
    backgroundColor: colors.background,
    alignItems: 'center',
    justifyContent: 'center',
  },
  errorText: {
    fontSize: fontSize.lg,
    color: colors.text,
    marginTop: spacing.md,
  },
  backButton: {
    marginTop: spacing.lg,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg,
    backgroundColor: colors.primary,
    borderRadius: borderRadius.md,
  },
  backButtonText: {
    color: colors.white,
    fontWeight: '600',
  },
});
