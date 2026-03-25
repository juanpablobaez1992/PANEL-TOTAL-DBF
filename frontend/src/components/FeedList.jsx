export function FeedList({ title, items }) {
  return (
    <section className="panel-card">
      <div className="section-head">
        <h3>{title}</h3>
      </div>
      <div className="feed-list">
        {items.length === 0 ? <p className="muted">Sin elementos por ahora.</p> : null}
        {items.map((item) => (
          <article className={`feed-item severity-${item.severidad}`} key={item.id}>
            <strong>{item.titulo}</strong>
            <p>{item.descripcion}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
