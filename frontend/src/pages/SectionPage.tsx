interface SectionPageProps {
  title: string;
  description: string;
}

/** Placeholder for a section whose feature hasn't been built yet. */
export function SectionPage({ title, description }: SectionPageProps) {
  return (
    <section>
      <h1 className="text-2xl font-bold">{title}</h1>
      <p className="mt-2 text-gray-700">{description}</p>
      <p className="mt-4 text-sm text-gray-600">This section is coming in a later sprint.</p>
    </section>
  );
}
