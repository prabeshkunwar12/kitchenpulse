export type DecimalString = string;
export type StockStatus = 'in_stock' | 'low_stock' | 'out_of_stock';
export type Unit = 'boxes' | 'bags' | 'cases' | 'pieces' | 'kilograms' | 'grams'
  | 'litres' | 'bottles' | 'buckets';

export interface Category {
  id: number;
  name: string;
}

export interface InventoryItem {
  id: number;
  name: string;
  category_id: number;
  unit: Unit;
  quantity: DecimalString;
  minimum: DecimalString;
  target: DecimalString;
  adjustment_step: DecimalString;
  recommended_replenishment: DecimalString;
  manual_low: boolean;
  stock_status: StockStatus;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StockTransaction {
  id: number;
  item_id: number;
  item_name: string;
  unit: Unit;
  type: 'opening' | 'add' | 'remove' | 'count' | 'reversal';
  quantity_change: DecimalString;
  previous_quantity: DecimalString;
  resulting_quantity: DecimalString;
  created_at: string;
  reason: string | null;
  idempotency_key: string;
  reverses_transaction_id: number | null;
  reversed_by_transaction_id: number | null;
  can_reverse: boolean;
}

interface HistoryPage {
  transactions: StockTransaction[];
  next_before_id: number | null;
}

export class ApiError extends Error {
  constructor(message: string, readonly uncertain = false) {
    super(message);
    this.name = 'ApiError';
  }
}

const apiUrl = process.env.EXPO_PUBLIC_API_URL?.trim().replace(/\/+$/, '');

async function request<T>(path: string, method = 'GET', body?: object): Promise<T> {
  if (!apiUrl || !/^https?:\/\//.test(apiUrl)) {
    throw new ApiError('Set EXPO_PUBLIC_API_URL in the tablet environment and restart Expo.');
  }
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);
  const isWrite = method !== 'GET';

  try {
    const response = await fetch(apiUrl + path, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
    if (!response.ok) {
      const result = await response.json().catch(() => undefined);
      const message = typeof result?.error?.message === 'string'
        ? result.error.message
        : `The API returned HTTP ${response.status}.`;
      const uncertain = isWrite && (
        response.status >= 500 || response.status === 408 || response.status === 429
      );
      throw new ApiError(message, uncertain);
    }
    if (response.headers.get('Content-Type')?.split(';')[0] !== 'application/json') {
      throw new ApiError('The configured address did not return inventory API data.', isWrite);
    }
    return await response.json() as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError('Could not reach the inventory API. Check the connection and try again.', isWrite);
  } finally {
    clearTimeout(timeout);
  }
}

export const inventoryApi = {
  categories: () => request<Category[]>('/categories'),
  items: () => request<InventoryItem[]>('/items'),
  history: (beforeId: number | null) => request<HistoryPage>(
    beforeId === null ? '/transactions' : `/transactions?before_id=${beforeId}`,
  ),
  adjust: (id: number, direction: 'add' | 'remove', key: string) => request<StockTransaction>(
    `/items/${id}/stock/${direction}`, 'POST', { idempotency_key: key },
  ),
  report: (id: number, manualLow: boolean) => request<InventoryItem>(
    `/items/${id}/report`, 'PATCH', { manual_low: manualLow },
  ),
  reverse: (id: number, key: string) => request<StockTransaction>(
    `/transactions/${id}/reverse`, 'POST', { idempotency_key: key },
  ),
};
