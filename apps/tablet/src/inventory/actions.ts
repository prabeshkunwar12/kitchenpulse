import { useMutation, useQueryClient } from '@tanstack/react-query';
import { randomUUID } from 'expo-crypto';
import { useRef, useState } from 'react';

import { ApiError, inventoryApi } from '../api/client';

export const itemKey = ['inventory', 'items'] as const;
export const historyKey = ['inventory', 'transactions'] as const;

type ActionFields =
  | { kind: 'add' | 'remove' }
  | { kind: 'report'; manualLow: boolean }
  | { kind: 'reverse'; transactionId: number };
type Action = ActionFields & { itemId: number; itemName: string; key: string };
type ActionFeedback =
  | { kind: 'success' | 'failure'; message: string }
  | { kind: 'uncertain'; message: string; action: Action };

async function send(action: Action) {
  switch (action.kind) {
    case 'add':
    case 'remove':
      await inventoryApi.adjust(action.itemId, action.kind, action.key);
      return action.kind === 'add' ? 'Stock added' : 'Stock removed';
    case 'report':
      await inventoryApi.report(action.itemId, action.manualLow);
      return action.manualLow ? 'Low stock reported' : 'Report cleared';
    case 'reverse':
      await inventoryApi.reverse(action.transactionId, action.key);
      return 'Transaction undone';
  }
}

export function useInventoryActions() {
  const queryClient = useQueryClient();
  const locked = useRef(new Set<number>());
  const unresolved = useRef(new Map<number, Action>());
  const [pending, setPending] = useState<number[]>([]);
  const [feedback, setFeedback] = useState<ActionFeedback[]>([]);
  const { mutateAsync } = useMutation({ mutationFn: send });

  function clearPrevious(itemId: number, key: string) {
    setFeedback((previous) => previous.filter(
      (entry) => entry.kind === 'uncertain' && (
        entry.action.itemId !== itemId || entry.action.key !== key
      ),
    ));
  }

  async function run(action: Action) {
    if (locked.current.has(action.itemId)) return;

    locked.current.add(action.itemId);
    setPending([...locked.current]);
    clearPrevious(action.itemId, action.key);

    try {
      const summary = await mutateAsync(action);
      unresolved.current.delete(action.itemId);
      setFeedback((previous) => [...previous.filter((entry) => entry.kind === 'uncertain'), {
        kind: 'success',
        message: `${summary} · ${action.itemName}`,
      }]);
    } catch (error) {
      if (error instanceof ApiError && error.uncertain) {
        unresolved.current.set(action.itemId, action);
        setFeedback((previous) => [...previous, {
          kind: 'uncertain',
          message: `Could not confirm the change for ${action.itemName}. Retry this same action.`,
          action,
        }]);
      } else {
        unresolved.current.delete(action.itemId);
        setFeedback((previous) => [...previous.filter((entry) => entry.kind === 'uncertain'), {
          kind: 'failure',
          message: error instanceof Error ? error.message : 'The stock action failed.',
        }]);
      }
    } finally {
      // A rejected action or replay can also reveal that the loaded item/history is stale.
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: itemKey }),
        queryClient.invalidateQueries({ queryKey: historyKey }),
      ]);
      locked.current.delete(action.itemId);
      setPending([...locked.current]);
    }
  }

  function start(itemId: number, itemName: string, fields: ActionFields) {
    if (locked.current.has(itemId) || unresolved.current.has(itemId)) return;
    void run({ ...fields, itemId, itemName, key: randomUUID() });
  }

  return { start, retry: run, pending, feedback };
}
