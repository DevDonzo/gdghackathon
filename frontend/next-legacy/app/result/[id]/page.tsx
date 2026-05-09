import { ResultSummary } from "@/components/result-summary";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function ResultPage({ params }: PageProps) {
  const { id } = await params;
  return <ResultSummary negotiationId={id} />;
}
