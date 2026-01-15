import React, { useEffect } from 'react';
import { Redirect } from 'expo-router';
import { useAuth } from '../src/context/AuthContext';
import LoadingSpinner from '../src/components/LoadingSpinner';

export default function Index() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <LoadingSpinner fullScreen message="Loading..." />;
  }

  // Redirect based on auth status
  if (isAuthenticated) {
    return <Redirect href="/orders" />;
  } else {
    return <Redirect href="/login" />;
  }
}
