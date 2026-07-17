import { useEffect, useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../hooks/useAuth';
import { getCategories, createCategory, deleteCategory, getTitleSummary, reassignCategory } from '../api/categories';
import { ApiError } from '../api/client';
import SectionHeading from '../components/ui/SectionHeading';
import AlertBanner from '../components/ui/AlertBanner';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import { formatCurrency } from '../lib/format';
import type { TitleSummaryRow } from '../types/api';

const RESERVED_NAMES = new Set(['Uncategorized', 'Ignored']);

export default function CategoriesPage() {
  const { premium } = useAuth();

  if (!premium?.isPremium) {
    return (
      <div className="page">
        <SectionHeading premium>Categories</SectionHeading>
        <AlertBanner kind="warning">
          Categories is a Premium feature. Start your free trial, pay with Xanax, or check faction
          options on the Settings page.
        </AlertBanner>
      </div>
    );
  }

  return <CategoriesContent />;
}

function CategoriesContent() {
  const queryClient = useQueryClient();
  const categoriesQuery = useQuery({ queryKey: ['categories'], queryFn: getCategories });

  const [newCategoryName, setNewCategoryName] = useState('');
  const [addError, setAddError] = useState<string | null>(null);
  const createMutation = useMutation({
    mutationFn: createCategory,
    onSuccess: () => {
      setNewCategoryName('');
      setAddError(null);
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
    onError: (err) => setAddError(err instanceof ApiError ? err.message : 'Something went wrong.'),
  });
  const deleteMutation = useMutation({
    mutationFn: deleteCategory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  function handleAddCategory(e: FormEvent) {
    e.preventDefault();
    const name = newCategoryName.trim();
    if (!name) {
      setAddError('Enter a name.');
      return;
    }
    if (RESERVED_NAMES.has(name)) {
      setAddError(`'${name}' is reserved and can't be used as a custom category.`);
      return;
    }
    createMutation.mutate(name);
  }

  return (
    <div className="page">
      <SectionHeading>Categories</SectionHeading>

      <SectionHeading>Manage Categories</SectionHeading>
      <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>
        Categories used across Sync, Dashboard, and auto-categorization. A category can only be
        removed once no log entries use it.
      </p>

      <Card>
        <form onSubmit={handleAddCategory} style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
          <div style={{ flex: 1 }}>
            <label htmlFor="new-category">New category name</label>
            <input id="new-category" value={newCategoryName} onChange={(e) => setNewCategoryName(e.target.value)} />
          </div>
          <Button type="submit" disabled={createMutation.isPending}>
            Add category
          </Button>
        </form>
      </Card>
      {addError && <AlertBanner kind="error">{addError}</AlertBanner>}

      <table>
        <thead>
          <tr>
            <th>Category</th>
            <th>Entries</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {(categoriesQuery.data?.categories ?? []).map((cat) => (
            <tr key={cat.name}>
              <td>{cat.name}</td>
              <td>
                {cat.entryCount} entr{cat.entryCount === 1 ? 'y' : 'ies'}
              </td>
              <td>
                <Button
                  variant="danger"
                  disabled={cat.entryCount > 0}
                  title={cat.entryCount > 0 ? 'Remove or recategorize its entries first' : undefined}
                  onClick={() => deleteMutation.mutate(cat.name)}
                >
                  Delete
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <hr />
      <ReviewAndRecategorize categories={(categoriesQuery.data?.categories ?? []).map((c) => c.name)} />
    </div>
  );
}

function effectiveSign(row: TitleSummaryRow): 1 | -1 {
  if (row.amountSign !== null) return row.amountSign;
  if (row.exampleAmount !== null && row.exampleAmount < 0) return -1;
  return 1;
}

interface RowEdit {
  category?: string;
  sign?: 1 | -1;
}

function ReviewAndRecategorize({ categories }: { categories: string[] }) {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<string>('All');
  const [titleSearch, setTitleSearch] = useState('');
  const summaryQuery = useQuery({
    queryKey: ['categories', 'titleSummary', filter],
    queryFn: () => getTitleSummary(filter === 'All' ? undefined : filter),
  });

  const [edits, setEdits] = useState<Record<string, RowEdit>>({});
  const [applyError, setApplyError] = useState<string | null>(null);
  useEffect(() => setEdits({}), [summaryQuery.data]);

  function rowKey(row: { title: string; category: string }): string {
    return `${row.title}::${row.category}`;
  }

  const reassignMutation = useMutation({
    mutationFn: (vars: { title: string; fromCategory: string; toCategory: string; amountSign: 1 | -1 | null }) =>
      reassignCategory(vars.title, vars.fromCategory, vars.toCategory, vars.amountSign),
  });

  const filterOptions = ['All', ...new Set([...categories, 'Uncategorized', 'Ignored'])];
  const categoryOptions = [...categories, 'Uncategorized', 'Ignored'];
  const allRows = summaryQuery.data?.rows ?? [];
  const rows = titleSearch.trim()
    ? allRows.filter((row) => (row.title ?? '').toLowerCase().includes(titleSearch.trim().toLowerCase()))
    : allRows;

  function rowChange(row: TitleSummaryRow): { categoryChanged: boolean; signChanged: boolean } {
    const edit = edits[rowKey(row)];
    return {
      categoryChanged: edit?.category !== undefined && edit.category !== row.category,
      signChanged: edit?.sign !== undefined && edit.sign !== effectiveSign(row),
    };
  }

  const changedRows = allRows.filter((row) => {
    const { categoryChanged, signChanged } = rowChange(row);
    return categoryChanged || signChanged;
  });

  async function handleApply() {
    setApplyError(null);
    try {
      for (const row of changedRows) {
        const edit = edits[rowKey(row)];
        const { signChanged } = rowChange(row);
        await reassignMutation.mutateAsync({
          title: row.title,
          fromCategory: row.category,
          toCategory: edit?.category ?? row.category,
          amountSign: signChanged ? (edit!.sign as 1 | -1) : null,
        });
      }
      setEdits({});
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['log-entries'] });
    } catch (err) {
      setApplyError(err instanceof ApiError ? err.message : 'Failed to apply changes.');
    }
  }

  return (
    <>
      <SectionHeading>Review &amp; Recategorize</SectionHeading>
      <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>
        Every log title seen so far, grouped by its current category. Edit the Category or Sign
        column and click Apply to reassign/re-sign all matching entries — both choices are also
        remembered for future syncs.
      </p>

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-end', marginBottom: 8 }}>
        <div>
          <label htmlFor="title-filter">Filter by category</label>
          <select id="title-filter" value={filter} onChange={(e) => setFilter(e.target.value)} style={{ maxWidth: 240 }}>
            {filterOptions.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="title-search">Search title</label>
          <input
            id="title-search"
            value={titleSearch}
            onChange={(e) => setTitleSearch(e.target.value)}
            placeholder="e.g. Attacked player"
            style={{ maxWidth: 240 }}
          />
        </div>
      </div>

      {allRows.length === 0 ? (
        <AlertBanner kind="info">No log entries yet.</AlertBanner>
      ) : rows.length === 0 ? (
        <AlertBanner kind="info">No titles match "{titleSearch}".</AlertBanner>
      ) : (
        <>
          <table>
            <thead>
              <tr>
                <th>Title</th>
                <th>Entries</th>
                <th>Amount</th>
                <th>Sign</th>
                <th>Category</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const key = rowKey(row);
                const sign = edits[key]?.sign ?? effectiveSign(row);
                return (
                  <tr key={key}>
                    <td>{row.title}</td>
                    <td>{row.entryCount}</td>
                    <td>{formatCurrency(row.exampleAmount)}</td>
                    <td>
                      <Button
                        onClick={() => setEdits((prev) => ({ ...prev, [key]: { ...prev[key], sign: sign === 1 ? -1 : 1 } }))}
                        disabled={row.exampleAmount === null}
                        title={row.exampleAmount === null ? 'No detected amount to sign' : 'Flip sign for every entry with this title'}
                      >
                        {sign === 1 ? '+' : '−'}
                      </Button>
                    </td>
                    <td>
                      <select
                        value={edits[key]?.category ?? row.category}
                        onChange={(e) => setEdits((prev) => ({ ...prev, [key]: { ...prev[key], category: e.target.value } }))}
                      >
                        {categoryOptions.map((c) => (
                          <option key={c} value={c}>
                            {c}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          <div style={{ marginTop: 12 }}>
            <Button variant="primary" onClick={handleApply} disabled={changedRows.length === 0 || reassignMutation.isPending}>
              Apply changes
            </Button>
          </div>
          {reassignMutation.isSuccess && changedRows.length === 0 && <AlertBanner kind="success">Changes applied.</AlertBanner>}
          {applyError && <AlertBanner kind="error">{applyError}</AlertBanner>}
        </>
      )}
    </>
  );
}
