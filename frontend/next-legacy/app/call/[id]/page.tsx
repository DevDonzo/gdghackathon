import { CallDashboard } from "@/components/call-dashboard";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function CallPage({ params }: PageProps) {
  const { id } = await params;
  return <CallDashboard negotiationId={id} />;
}
