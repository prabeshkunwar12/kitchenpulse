import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import {
  ActivityIndicator, FlatList, Modal, ScrollView, StyleSheet, Text, TextInput, View,
  useWindowDimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { inventoryApi, type StockTransaction } from '../api/client';
import { historyKey, itemKey, useInventoryActions } from './actions';
import { Button, colors, HistoryRow, ItemCard } from './components';

const tabs = [
  { id: 'inventory', name: 'Inventory' },
  { id: 'attention', name: 'Needs attention' },
  { id: 'history', name: 'History' },
] as const;

type Tab = typeof tabs[number]['id'];

function LoadMessage({ loading, message }: { loading?: boolean; message: string }) {
  return (
    <View style={styles.message} accessibilityLiveRegion="polite">
      {loading && <ActivityIndicator color={colors.green} />}
      <Text style={styles.messageText}>{message}</Text>
    </View>
  );
}

export function InventoryScreen() {
  const [tab, setTab] = useState<Tab>('inventory');
  const [category, setCategory] = useState<number | null>(null);
  const [search, setSearch] = useState('');
  const [confirm, setConfirm] = useState<StockTransaction | null>(null);
  const { width } = useWindowDimensions();
  const columns = width >= 1040 ? 3 : width >= 670 ? 2 : 1;
  const showingHistory = tab === 'history';

  const categories = useQuery({ queryKey: ['inventory', 'categories'], queryFn: inventoryApi.categories });
  const items = useQuery({ queryKey: itemKey, queryFn: inventoryApi.items });
  const history = useInfiniteQuery({
    queryKey: historyKey,
    queryFn: ({ pageParam }) => inventoryApi.history(pageParam),
    initialPageParam: null as number | null,
    getNextPageParam: (page) => page.next_before_id ?? undefined,
    enabled: showingHistory,
  });
  const actions = useInventoryActions();
  const pendingItems = new Set(actions.pending);
  for (const entry of actions.feedback) {
    if (entry.kind === 'uncertain') pendingItems.add(entry.action.itemId);
  }

  const categoryNames = new Map(categories.data?.map((entry) => [entry.id, entry.name]));
  const searchTerm = search.trim().toLowerCase();
  const visibleItems = items.data?.filter((item) => {
    const needsAttention = item.stock_status !== 'in_stock' || item.manual_low;
    const searchable = `${item.name} ${categoryNames.get(item.category_id) ?? ''}`.toLowerCase();
    return (tab !== 'attention' || needsAttention)
      && (category === null || item.category_id === category)
      && searchable.includes(searchTerm);
  }) ?? [];
  const latestHistory = history.data?.pages.flatMap((page) => page.transactions) ?? [];
  const isLoading = showingHistory ? history.isPending : items.isPending || categories.isPending;
  const isRefreshing = showingHistory ? history.isFetching : items.isFetching || categories.isFetching;
  const loadError = showingHistory ? history.error : items.error || categories.error;
  const hasUsableData = showingHistory ? !!history.data : !!items.data && !!categories.data;

  function refresh() {
    if (showingHistory) void history.refetch();
    else void Promise.all([items.refetch(), categories.refetch()]);
  }

  return (
    <SafeAreaView style={styles.screen}>
      <View style={styles.header}>
        <Text style={styles.title} accessibilityRole="header">KitchenPulse</Text>
        <View style={styles.toolbar}>
          {tabs.map(({ id, name }) => (
            <Button key={id} selected={tab === id} onPress={() => setTab(id)}>{name}</Button>
          ))}
          <Button onPress={refresh} disabled={isRefreshing} label="Refresh inventory data">
            {isRefreshing ? 'Refreshing…' : 'Refresh'}
          </Button>
        </View>
      </View>

      {!showingHistory && (
        <View style={styles.filters}>
          <TextInput
            accessibilityLabel="Search inventory"
            placeholder="Search products or categories"
            placeholderTextColor={colors.muted}
            value={search}
            onChangeText={setSearch}
            autoCorrect={false}
            autoCapitalize="none"
            clearButtonMode="while-editing"
            style={styles.search}
          />
          <ScrollView
            horizontal
            keyboardShouldPersistTaps="handled"
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.categories}
          >
            <Button selected={category === null} onPress={() => setCategory(null)}>All categories</Button>
            {categories.data?.map((entry) => (
              <Button key={entry.id} selected={category === entry.id} onPress={() => setCategory(entry.id)}>
                {entry.name}
              </Button>
            ))}
          </ScrollView>
        </View>
      )}

      {actions.feedback.length > 0 && (
        <ScrollView style={styles.feedbackList} keyboardShouldPersistTaps="handled">
          {actions.feedback.map((entry) => (
            <View
              key={entry.kind === 'uncertain' ? entry.action.key : entry.kind}
              style={[styles.feedback, entry.kind !== 'success' && styles.feedbackError]}
            >
              <Text
                accessibilityLiveRegion="polite"
                style={[styles.feedbackText, entry.kind !== 'success' && styles.feedbackErrorText]}
              >
                {entry.message}
              </Text>
              {entry.kind === 'uncertain' && (
                <Button
                  label={`Retry stock action for ${entry.action.itemName}`}
                  onPress={() => { void actions.retry(entry.action); }}
                >
                  Retry action
                </Button>
              )}
            </View>
          ))}
        </ScrollView>
      )}

      {loadError && (
        <View style={[styles.feedback, styles.feedbackError]}>
          <Text accessibilityLiveRegion="polite" style={[styles.feedbackText, styles.feedbackErrorText]}>
            {hasUsableData ? 'Showing the last loaded data. ' : ''}{loadError.message}
          </Text>
          <Button onPress={refresh} disabled={isRefreshing}>Try again</Button>
        </View>
      )}

      {!hasUsableData && isLoading && !loadError && (
        <LoadMessage loading message={showingHistory ? 'Loading history…' : 'Loading inventory…'} />
      )}

      {hasUsableData && (showingHistory ? (
        <FlatList
          key="history"
          data={latestHistory}
          keyExtractor={(entry) => String(entry.id)}
          renderItem={({ item }) => (
            <HistoryRow entry={item} busy={pendingItems.has(item.item_id)} onUndo={() => setConfirm(item)} />
          )}
          contentContainerStyle={styles.list}
          ListEmptyComponent={<LoadMessage message="No stock transactions yet." />}
          ListFooterComponent={history.hasNextPage ? (
            <Button onPress={() => { void history.fetchNextPage(); }} disabled={history.isFetching}>
              {history.isFetchingNextPage ? 'Loading…' : 'Load older transactions'}
            </Button>
          ) : undefined}
        />
      ) : (
        <FlatList
          key={`items-${columns}`}
          data={visibleItems}
          numColumns={columns}
          columnWrapperStyle={columns > 1 ? styles.gridRow : undefined}
          contentContainerStyle={styles.list}
          keyboardShouldPersistTaps="handled"
          keyExtractor={(item) => String(item.id)}
          renderItem={({ item }) => (
            <View style={styles.gridCell}>
              <ItemCard
                item={item}
                category={categoryNames.get(item.category_id) ?? 'Uncategorized'}
                busy={pendingItems.has(item.id)}
                onAdjust={(kind) => actions.start(item.id, item.name, { kind })}
                onReport={(manualLow) => actions.start(item.id, item.name, { kind: 'report', manualLow })}
              />
            </View>
          )}
          ListEmptyComponent={<LoadMessage message={
            searchTerm || category !== null
              ? 'No products match these filters.'
              : tab === 'attention' ? 'No products need attention.' : 'No inventory items yet.'
          } />}
        />
      ))}

      {confirm && (
        <Modal visible transparent animationType="fade" onRequestClose={() => setConfirm(null)}>
          <View style={styles.overlay}>
            <View style={styles.dialog} accessibilityViewIsModal>
              <Text style={styles.dialogTitle} accessibilityRole="header">Undo this transaction?</Text>
              <Text style={styles.messageText}>
                KitchenPulse will record a reversal for {confirm.item_name}.
              </Text>
              <View style={styles.toolbar}>
                <Button onPress={() => setConfirm(null)}>Cancel</Button>
                <Button primary onPress={() => {
                  actions.start(confirm.item_id, confirm.item_name, { kind: 'reverse', transactionId: confirm.id });
                  setConfirm(null);
                }}>
                  Confirm undo
                </Button>
              </View>
            </View>
          </View>
        </Modal>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.canvas, paddingHorizontal: 18 },
  header: {
    flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between',
    gap: 10, paddingTop: 10, paddingBottom: 12,
  },
  title: { color: colors.ink, fontSize: 30, fontWeight: '800', letterSpacing: -0.5 },
  toolbar: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  filters: { gap: 9, paddingBottom: 12 },
  search: {
    minHeight: 46, paddingHorizontal: 13, color: colors.ink, fontSize: 16, backgroundColor: colors.white,
    borderWidth: 1, borderColor: colors.line, borderRadius: 10,
  },
  categories: { flexDirection: 'row', gap: 8 },
  list: { gap: 11, paddingBottom: 18 },
  gridRow: { gap: 11 },
  gridCell: { flex: 1, minWidth: 0 },
  message: { alignItems: 'center', gap: 12, padding: 28 },
  messageText: { fontSize: 16, lineHeight: 23, color: colors.muted },
  feedbackList: { flexGrow: 0, maxHeight: 130 },
  feedback: {
    flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: 8, paddingHorizontal: 12,
    paddingVertical: 8, marginBottom: 9, borderRadius: 10, backgroundColor: colors.pale,
  },
  feedbackError: { backgroundColor: colors.redBackground },
  feedbackText: { flex: 1, minWidth: 150, color: colors.green, fontSize: 15, fontWeight: '600' },
  feedbackErrorText: { color: colors.red },
  overlay: {
    flex: 1, alignItems: 'center', justifyContent: 'center', padding: 20,
    backgroundColor: 'rgba(17, 37, 33, 0.54)',
  },
  dialog: {
    width: '100%', maxWidth: 470, borderRadius: 16, gap: 14, padding: 24, backgroundColor: colors.white,
  },
  dialogTitle: { fontSize: 22, fontWeight: '700', color: colors.ink },
});
