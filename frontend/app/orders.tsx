import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  TouchableOpacity,
  RefreshControl,
  Alert,
} from 'react-native';
import { Stack, router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { useAuth } from '../src/context/AuthContext';
import { ordersAPI } from '../src/services/api';
import { colors, spacing, fontSize, borderRadius, ORDER_STATUS_CONFIG } from '../src/constants/theme';
import OrderCard from '../src/components/OrderCard';
import LoadingSpinner from '../src/components/LoadingSpinner';
import { addNotificationReceivedListener, addNotificationResponseReceivedListener } from '../src/services/notifications';

type OrderStatus = 'all' | 'pending' | 'payment_pending' | 'paid' | 'confirmed' | 'processing' | 'shipped' | 'delivered' | 'cancelled';

const STATUS_TABS: { key: OrderStatus; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'pending', label: 'Pending' },
  { key: 'paid', label: 'Paid' },
  { key: 'confirmed', label: 'Confirmed' },
  { key: 'shipped', label: 'Shipped' },
  { key: 'delivered', label: 'Delivered' },
];

export default function OrdersScreen() {
  const { logout, user } = useAuth();
  const [orders, setOrders] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState<OrderStatus>('all');
  const [stats, setStats] = useState<any>(null);

  // Fetch orders
  const fetchOrders = async (showLoader = true) => {
    try {
      if (showLoader) setIsLoading(true);
      
      const params: any = { limit: 100 };
      if (selectedStatus !== 'all') {
        params.status = selectedStatus;
      }
      
      const data = await ordersAPI.getOrders(params);
      setOrders(Array.isArray(data) ? data : data.orders || []);
    } catch (error: any) {
      console.error('Error fetching orders:', error);
      if (error.response?.status === 401) {
        Alert.alert('Session Expired', 'Please login again');
        logout();
      }
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  // Fetch stats
  const fetchStats = async () => {
    try {
      const data = await ordersAPI.getOrderStats();
      setStats(data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  // Initial load and refresh on focus
  useFocusEffect(
    useCallback(() => {
      fetchOrders();
      fetchStats();
    }, [selectedStatus])
  );

  // Setup notification listeners
  useEffect(() => {
    const receivedSubscription = addNotificationReceivedListener((notification) => {
      console.log('Notification received:', notification);
      // Refresh orders when new notification comes in
      fetchOrders(false);
    });

    const responseSubscription = addNotificationResponseReceivedListener((response) => {
      console.log('Notification response:', response);
      const data = response.notification.request.content.data;
      // Navigate to order details if order_id is present
      if (data?.order_id) {
        router.push(`/order/${data.order_id}`);
      }
    });

    return () => {
      receivedSubscription.remove();
      responseSubscription.remove();
    };
  }, []);

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchOrders(false);
    fetchStats();
  };

  const handleLogout = () => {
    Alert.alert(
      'Logout',
      'Are you sure you want to logout?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Logout',
          style: 'destructive',
          onPress: async () => {
            await logout();
            router.replace('/login');
          },
        },
      ]
    );
  };

  const renderStatusTab = ({ item }: { item: typeof STATUS_TABS[0] }) => (
    <TouchableOpacity
      style={[
        styles.statusTab,
        selectedStatus === item.key && styles.statusTabActive,
      ]}
      onPress={() => setSelectedStatus(item.key)}
    >
      <Text
        style={[
          styles.statusTabText,
          selectedStatus === item.key && styles.statusTabTextActive,
        ]}
      >
        {item.label}
      </Text>
    </TouchableOpacity>
  );

  const renderOrder = ({ item }: { item: any }) => (
    <OrderCard
      order={item}
      onPress={() => router.push(`/order/${item.id}`)}
    />
  );

  const renderEmptyList = () => (
    <View style={styles.emptyContainer}>
      <Ionicons name="cube-outline" size={64} color={colors.textMuted} />
      <Text style={styles.emptyText}>No orders found</Text>
      <Text style={styles.emptySubtext}>
        {selectedStatus === 'all'
          ? 'Orders will appear here'
          : `No ${selectedStatus} orders`}
      </Text>
    </View>
  );

  return (
    <View style={styles.container}>
      <Stack.Screen
        options={{
          title: 'Orders',
          headerRight: () => (
            <TouchableOpacity onPress={handleLogout} style={styles.logoutButton}>
              <Ionicons name="log-out-outline" size={24} color={colors.text} />
            </TouchableOpacity>
          ),
        }}
      />

      {/* Stats Summary */}
      {stats && (
        <View style={styles.statsContainer}>
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{stats.total_orders || 0}</Text>
            <Text style={styles.statLabel}>Total</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statItem}>
            <Text style={[styles.statValue, { color: colors.warning }]}>
              {stats.pending_orders || 0}
            </Text>
            <Text style={styles.statLabel}>Pending</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statItem}>
            <Text style={[styles.statValue, { color: colors.success }]}>
              {stats.today_orders || 0}
            </Text>
            <Text style={styles.statLabel}>Today</Text>
          </View>
        </View>
      )}

      {/* Status Tabs */}
      <FlatList
        horizontal
        data={STATUS_TABS}
        renderItem={renderStatusTab}
        keyExtractor={(item) => item.key}
        showsHorizontalScrollIndicator={false}
        style={styles.statusTabs}
        contentContainerStyle={styles.statusTabsContent}
      />

      {/* Orders List */}
      {isLoading ? (
        <LoadingSpinner fullScreen message="Loading orders..." />
      ) : (
        <FlatList
          data={orders}
          renderItem={renderOrder}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.listContent}
          refreshControl={
            <RefreshControl
              refreshing={isRefreshing}
              onRefresh={handleRefresh}
              tintColor={colors.primary}
              colors={[colors.primary]}
            />
          }
          ListEmptyComponent={renderEmptyList}
          showsVerticalScrollIndicator={false}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  logoutButton: {
    padding: spacing.sm,
  },
  statsContainer: {
    flexDirection: 'row',
    backgroundColor: colors.surface,
    marginHorizontal: spacing.md,
    marginTop: spacing.md,
    padding: spacing.md,
    borderRadius: borderRadius.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  statItem: {
    flex: 1,
    alignItems: 'center',
  },
  statValue: {
    fontSize: fontSize.xxl,
    fontWeight: '700',
    color: colors.text,
  },
  statLabel: {
    fontSize: fontSize.xs,
    color: colors.textMuted,
    marginTop: spacing.xs,
  },
  statDivider: {
    width: 1,
    backgroundColor: colors.border,
  },
  statusTabs: {
    marginTop: spacing.md,
    maxHeight: 48,
  },
  statusTabsContent: {
    paddingHorizontal: spacing.md,
    gap: spacing.sm,
  },
  statusTab: {
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderRadius: borderRadius.full,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  statusTabActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  statusTabText: {
    fontSize: fontSize.sm,
    color: colors.textSecondary,
    fontWeight: '500',
  },
  statusTabTextActive: {
    color: colors.white,
  },
  listContent: {
    padding: spacing.md,
    paddingBottom: spacing.xxl,
  },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.xxl * 2,
  },
  emptyText: {
    fontSize: fontSize.lg,
    color: colors.text,
    marginTop: spacing.md,
  },
  emptySubtext: {
    fontSize: fontSize.sm,
    color: colors.textMuted,
    marginTop: spacing.xs,
  },
});
