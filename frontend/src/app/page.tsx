export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="text-center space-y-6">
        <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-6xl">
          🇨🇦 VisaCanada
        </h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          Plateforme IA de gestion d&apos;immigration canadienne.
          Accompagnez vos candidats de A à Z avec l&apos;intelligence artificielle.
        </p>
        <div className="flex gap-4 justify-center">
          <a
            href="/docs"
            className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-sm hover:opacity-90"
          >
            API Documentation
          </a>
          <a
            href="https://github.com/romuald2/visacanada"
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-md bg-secondary px-4 py-2 text-sm font-semibold text-secondary-foreground shadow-sm hover:opacity-90"
          >
            GitHub
          </a>
        </div>
      </div>
    </main>
  );
}
