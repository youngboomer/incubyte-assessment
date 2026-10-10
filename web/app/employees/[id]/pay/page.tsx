import type { Metadata } from "next";
import { Shell } from "../../../../components/shell";

export const metadata: Metadata = { title: "Change pay – CompPulse" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <Shell>
      <h1>Change pay</h1>
      <p>Employee {id}. Coming next.</p>
    </Shell>
  );
}
