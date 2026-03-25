import { useEffect, useMemo, useState } from "react";

export function ProgramForm({ onSubmit, onCancel, currentValue, loading }) {
  const [programadaPara, setProgramadaPara] = useState("");
  const minValue = useMemo(() => new Date().toISOString().slice(0, 16), []);

  useEffect(() => {
    setProgramadaPara(currentValue ? new Date(currentValue).toISOString().slice(0, 16) : "");
  }, [currentValue]);

  return (
    <form
      className="program-form"
      onSubmit={(event) => {
        event.preventDefault();
        if (!programadaPara) return;
        onSubmit(programadaPara);
      }}
    >
      <label className="field-stack">
        Programar fecha y hora
        <input
          min={minValue}
          onChange={(event) => setProgramadaPara(event.target.value)}
          type="datetime-local"
          value={programadaPara}
        />
      </label>
      <div className="inline-actions">
        <button disabled={!programadaPara || loading} type="submit">
          Guardar programacion
        </button>
        <button className="ghost-button" disabled={loading} onClick={onCancel} type="button">
          Cancelar
        </button>
      </div>
    </form>
  );
}
