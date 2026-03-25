export function NewsFilters({ filters, onChange }) {
  return (
    <div className="filters-row">
      <input
        placeholder="Buscar por hecho, titulo o lugar"
        value={filters.q}
        onChange={(event) => onChange({ ...filters, q: event.target.value })}
      />
      <select value={filters.estado} onChange={(event) => onChange({ ...filters, estado: event.target.value })}>
        <option value="">Todos los estados</option>
        <option value="borrador">Borrador</option>
        <option value="generado">Generado</option>
        <option value="aprobado">Aprobado</option>
        <option value="publicado">Publicado</option>
        <option value="error">Error</option>
      </select>
      <label className="checkbox">
        <input
          checked={filters.soloProgramadas}
          type="checkbox"
          onChange={(event) => onChange({ ...filters, soloProgramadas: event.target.checked })}
        />
        Solo programadas
      </label>
    </div>
  );
}
