import { type ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { InventoryItem, StockTransaction } from '../api/client';

export const colors = {
  ink: '#152b28',
  muted: '#4c625c',
  line: '#d1ddd8',
  white: '#ffffff',
  canvas: '#eef3f1',
  pale: '#e4f1ea',
  green: '#145841',
  amber: '#784300',
  amberBackground: '#fff1d6',
  red: '#982e2d',
  redBackground: '#fbe8e6',
};

export function formatQuantity(value: string) {
  return value.replace(/(\.\d*?)0+$/, '$1').replace(/\.$/, '');
}

interface ButtonProps {
  children: ReactNode;
  onPress: () => void;
  label?: string;
  selected?: boolean;
  primary?: boolean;
  disabled?: boolean;
  large?: boolean;
}

export function Button({ children, onPress, label, selected, primary, disabled, large }: ButtonProps) {
  const filled = selected || primary;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled, selected }}
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        filled && styles.buttonFilled,
        large && styles.largeButton,
        pressed && styles.pressed,
        disabled && styles.disabled,
      ]}
    >
      <Text style={[styles.buttonText, filled && styles.buttonTextFilled]}>{children}</Text>
    </Pressable>
  );
}

const statuses = {
  out_of_stock: { label: 'Out of stock', text: colors.red, background: colors.redBackground },
  low_stock: { label: 'Low stock', text: colors.amber, background: colors.amberBackground },
  in_stock: { label: 'In stock', text: colors.green, background: colors.pale },
};

interface ItemCardProps {
  item: InventoryItem;
  category: string;
  busy: boolean;
  onAdjust: (direction: 'add' | 'remove') => void;
  onReport: (manualLow: boolean) => void;
}

export function ItemCard({ item, category, busy, onAdjust, onReport }: ItemCardProps) {
  const status = statuses[item.stock_status];
  const step = formatQuantity(item.adjustment_step);
  const insufficient = Number(item.quantity) < Number(item.adjustment_step);

  return (
    <View style={styles.card}>
      <Text style={styles.secondary}>{category}</Text>
      <Text accessibilityRole="header" style={styles.cardTitle}>{item.name}</Text>
      <View style={styles.statusRow}>
        <Text style={[styles.badge, { color: status.text, backgroundColor: status.background }]}>
          {status.label}
        </Text>
        {item.manual_low && <Text style={styles.manualBadge}>Reported low</Text>}
      </View>
      <Text style={styles.balance}>
        {formatQuantity(item.quantity)} <Text style={styles.unit}>{item.unit}</Text>
      </Text>
      <Text style={styles.secondary}>
        Min {formatQuantity(item.minimum)} · Target {formatQuantity(item.target)}
      </Text>
      {item.stock_status !== 'in_stock' || item.manual_low
        ? <Text style={styles.secondary}>Restock to target · {formatQuantity(item.recommended_replenishment)} {item.unit}</Text>
        : null}
      <View style={styles.adjustments}>
        <Button large disabled={busy || insufficient} onPress={() => onAdjust('remove')}
          label={`Remove ${step} ${item.unit} from ${item.name}`}>
          −{step}
        </Button>
        <Button large primary disabled={busy} onPress={() => onAdjust('add')}
          label={`Add ${step} ${item.unit} to ${item.name}`}>
          +{step}
        </Button>
      </View>
      <Button disabled={busy} onPress={() => onReport(!item.manual_low)}
        label={`${item.manual_low ? 'Clear report for' : 'Report low stock for'} ${item.name}`}>
        {item.manual_low ? 'Clear report' : 'Report low stock'}
      </Button>
    </View>
  );
}

const transactionLabels: Record<StockTransaction['type'], string> = {
  opening: 'Opening balance',
  add: 'Stock added',
  remove: 'Stock removed',
  count: 'Physical count',
  reversal: 'Reversal',
};

export function HistoryRow({ entry, busy, onUndo }: {
  entry: StockTransaction;
  busy: boolean;
  onUndo: () => void;
}) {
  const change = formatQuantity(entry.quantity_change);
  const signed = Number(entry.quantity_change) > 0 ? `+${change}` : change;
  return (
    <View style={[styles.card, styles.historyRow]}>
      <View style={styles.historyBody}>
        <Text accessibilityRole="header" style={styles.cardTitle}>{entry.item_name}</Text>
        <Text style={styles.secondary}>
          {transactionLabels[entry.type]} · {new Date(entry.created_at).toLocaleString()}
        </Text>
        {entry.reason && <Text style={styles.secondary}>{entry.reason}</Text>}
        {entry.reverses_transaction_id !== null && (
          <Text style={styles.secondary}>Reverses transaction #{entry.reverses_transaction_id}</Text>
        )}
        {entry.reversed_by_transaction_id !== null && (
          <Text style={styles.secondary}>Undone by transaction #{entry.reversed_by_transaction_id}</Text>
        )}
      </View>
      <View style={styles.historyAmount}>
        <Text style={styles.historyChange}>{signed} {entry.unit}</Text>
        <Text style={styles.secondary}>
          {formatQuantity(entry.previous_quantity)} → {formatQuantity(entry.resulting_quantity)}
        </Text>
      </View>
      {entry.can_reverse && (
        <Button disabled={busy} onPress={onUndo}
          label={`Undo transaction ${entry.id} for ${entry.item_name}`}>
          Undo
        </Button>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  button: {
    alignItems: 'center', justifyContent: 'center', minHeight: 46, minWidth: 52,
    paddingHorizontal: 13, paddingVertical: 7, borderRadius: 10, borderWidth: 1,
    borderColor: colors.line, backgroundColor: colors.white,
  },
  buttonFilled: { backgroundColor: colors.green, borderColor: colors.green },
  buttonText: { color: colors.ink, fontSize: 15, fontWeight: '700', textAlign: 'center' },
  buttonTextFilled: { color: colors.white },
  largeButton: { flex: 1, minHeight: 54 },
  pressed: { opacity: 0.75 },
  disabled: { opacity: 0.46 },
  card: {
    flex: 1, minWidth: 0, padding: 16, gap: 8, backgroundColor: colors.white,
    borderWidth: 1, borderColor: colors.line, borderRadius: 16,
  },
  cardTitle: { color: colors.ink, fontSize: 21, fontWeight: '700' },
  secondary: { color: colors.muted, fontSize: 14, lineHeight: 20 },
  balance: { color: colors.ink, fontSize: 35, fontWeight: '800', fontVariant: ['tabular-nums'] },
  unit: { color: colors.muted, fontSize: 16, fontWeight: '600' },
  statusRow: { flexDirection: 'row', gap: 6, flexWrap: 'wrap' },
  badge: { fontSize: 13, fontWeight: '700', paddingHorizontal: 9, paddingVertical: 4, borderRadius: 8 },
  manualBadge: {
    color: colors.amber, backgroundColor: colors.amberBackground, fontSize: 13, fontWeight: '700',
    paddingHorizontal: 9, paddingVertical: 4, borderRadius: 8,
  },
  adjustments: { flexDirection: 'row', gap: 8, marginTop: 'auto' },
  historyRow: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', gap: 16 },
  historyBody: { flexGrow: 1, flexShrink: 1, minWidth: 180, gap: 3 },
  historyAmount: { gap: 3 },
  historyChange: { color: colors.ink, fontSize: 17, fontWeight: '700' },
});
