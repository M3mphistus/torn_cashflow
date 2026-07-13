export default function ColdStartLoader() {
  return (
    <div className="page" style={{ textAlign: 'center', paddingTop: '15vh' }}>
      <p className="eyebrow">A SPEAKEASY LEDGER FOR TORN CITY</p>
      <h1>Waking up the server&hellip;</h1>
      <p>
        The backend spins down after a period of inactivity — this can take up to a minute the
        first time. Hang tight, it only happens once per idle period.
      </p>
    </div>
  );
}
