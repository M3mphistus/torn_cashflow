import { Link } from 'react-router-dom';
import Card from '../ui/Card';
import SectionHeading from '../ui/SectionHeading';

export default function NavCard({
  to,
  title,
  caption,
  premium = false,
}: {
  to: string;
  title: string;
  caption: string;
  premium?: boolean;
}) {
  return (
    <Link to={to} className="nav-card">
      <Card>
        <SectionHeading premium={premium}>{title}</SectionHeading>
        <p style={{ color: 'var(--text-mute)', fontSize: 13 }}>{caption}</p>
      </Card>
    </Link>
  );
}
