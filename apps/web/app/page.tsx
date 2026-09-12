import { ConnectionStatus } from "../components/connection-status";
import Link from "next/link";

export default function Home() {
  return (
    <div className="shell">
      <header>
        <Link
          className="brand"
          href="/"
          aria-label="Placement Intelligence home"
        >
          <span className="brand-mark">P</span>Placement Intelligence
        </Link>
        <span className="preview">Development preview</span>
      </header>
      <main id="main">
        <section className="intro">
          <p className="eyebrow">CAMPUS PLACEMENTS · ONE CLEAR PICTURE</p>
          <h1>
            Your next opportunity.
            <br />
            <span>A clearer way forward.</span>
          </h1>
          <p className="lede">
            Know where you stand with company requirements, your academic
            records, and your college’s placement policy in one place.
          </p>
          <ConnectionStatus />
        </section>
        <section aria-labelledby="workspace-title">
          <div className="section-heading">
            <h2 id="workspace-title">Your placement workspace</h2>
            <span>Coming in the decision MVP</span>
          </div>
          <div className="cards">
            {[
              [
                "01",
                "Your profile",
                "Verified academics, placement history, and dream-company preferences.",
              ],
              [
                "02",
                "Campus opportunities",
                "Company roles and requirements for each upcoming placement drive.",
              ],
              [
                "03",
                "Eligibility, explained",
                "Clear criteria, compared values, and the policy behind every result.",
              ],
            ].map(([number, title, description]) => (
              <article key={number}>
                <span className="number">{number}</span>
                <h3>{title}</h3>
                <p>{description}</p>
                <span className="upcoming">Planned</span>
              </article>
            ))}
          </div>
        </section>
        <aside>
          <span className="aside-icon" aria-hidden="true">
            ↗
          </span>
          <div>
            <h2>Built around your college’s rules</h2>
            <p>
              Eligibility will use verified records and approved policies. AI
              explanations will help you understand the result.
            </p>
          </div>
        </aside>
      </main>
      <footer>
        <span>Placement Intelligence</span>
        <span>Foundation preview · No student records loaded</span>
      </footer>
    </div>
  );
}
