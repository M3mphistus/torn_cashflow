import { useEffect, useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../hooks/useAuth';
import { getCategories, createCategory, deleteCategory, getTitleSummary, reassignCategory } from '../api/categories';
import { ApiError } from '../api/client';
import SectionHeading from '../components/ui/SectionHeading';
import AlertBanner from '../components/ui/AlertBanner';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';

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
    },
    onError: (err) => setAddError(err instanceof ApiError ? err.message : 'Something went wrong.'),
  });
  const deleteMutation = useMutation({
    mutationFn: deleteCategory,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['categories'] }),
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

function ReviewAndRecategorize({ categories }: { categories: string[] }) {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<string>('All');
  const summaryQuery = useQuery({
    queryKey: ['categories', 'titleSummary', filter],
    queryFn: () => getTitleSummary(filter === 'All' ? undefined : filter),
  });

  const [edits, setEdits] = useState<Record<string, string>>({});
  useEffect(() => setEdits({}), [summaryQuery.data]);

  function rowKey(row: { title: string; category: string }): string {
    return `${row.title}::${row.category}`;
  }

  // Note: Task 4's `reassignCategory` has the positional signature
  // `(title, fromCategory, toCategory)`, not the single-object signature the plan's
  // example code assumes. Adapting the mutationFn to that real signature here; the
  // call site below (`reassignMutation.mutateAsync({...})`) is left exactly as the
  // brief specifies.
  const reassignMutation = useMutation({
    mutationFn: (vars: { title: string; fromCategory: string; toCategory: string }) =>
      reassignCategory(vars.title, vars.fromCategory, vars.toCategory),
  });

  const filterOptions = ['All', ...categories, 'Uncategorized', 'Ignored'];
  const categoryOptions = [...categories, 'Uncategorized', 'Ignored'];
  const rows = summaryQuery.data?.rows ?? [];
  const changedCount = rows.filter((row) => edits[rowKey(row)] && edits[rowKey(row)] !== row.category).length;

  async function handleApply() {
    const changedRows = rows.filter((row) => edits[rowKey(row)] && edits[rowKey(row)] !== row.category);
    for (const row of changedRows) {
      await reassignMutation.mutateAsync({ title: row.title, fromCategory: row.category, toCategory: edits[rowKey(row)] });
    }
    setEdits({});
    queryClient.invalidateQueries({ queryKey: ['categories'] });
  }

  return (
    <>
      <SectionHeading>Review &amp; Recategorize</SectionHeading>
      <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>
        Every log title seen so far, grouped by its current category. Edit the Category column and
        click Apply to reassign all matching entries — the choice is also remembered for future
        syncs.
      </p>

      <label htmlFor="title-filter">Filter by category</label>
      <select id="title-filter" value={filter} onChange={(e) => setFilter(e.target.value)} style={{ maxWidth: 240 }}>
        {filterOptions.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>

      {rows.length === 0 ? (
        <AlertBanner kind="info">No log entries yet.</AlertBanner>
      ) : (
        <>
          <table>
            <thead>
              <tr>
                <th>Title</th>
                <th>Entries</th>
                <th>Category</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={rowKey(row)}>
                  <td>{row.title}</td>
                  <td>{row.entryCount}</td>
                  <td>
                    <select
                      value={edits[rowKey(row)] ?? row.category}
                      onChange={(e) => setEdits((prev) => ({ ...prev, [rowKey(row)]: e.target.value }))}
                    >
                      {categoryOptions.map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div style={{ marginTop: 12 }}>
            <Button variant="primary" onClick={handleApply} disabled={changedCount === 0 || reassignMutation.isPending}>
              Apply changes
            </Button>
          </div>
          {reassignMutation.isSuccess && changedCount === 0 && <AlertBanner kind="success">Changes applied.</AlertBanner>}
        </>
      )}
    </>
  );
}
