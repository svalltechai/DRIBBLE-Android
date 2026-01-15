import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { getStatusConfig, borderRadius, fontSize } from '../constants/theme';

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md';
}

export default function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const config = getStatusConfig(status);
  
  return (
    <View style={[
      styles.badge,
      { backgroundColor: config.bgColor },
      size === 'sm' && styles.badgeSm,
    ]}>
      <View style={[styles.dot, { backgroundColor: config.color }]} />
      <Text style={[
        styles.text,
        { color: config.color },
        size === 'sm' && styles.textSm,
      ]}>
        {config.label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: borderRadius.full,
    alignSelf: 'flex-start',
  },
  badgeSm: {
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    marginRight: 6,
  },
  text: {
    fontSize: fontSize.sm,
    fontWeight: '600',
  },
  textSm: {
    fontSize: fontSize.xs,
  },
});
