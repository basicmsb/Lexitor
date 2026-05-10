"use client";

import { useParams, useRouter } from "next/navigation";

import { DonAnalysisView } from "@/components/don/DonAnalysisView";

export default function DonDocumentDetailPage() {
  const params = useParams<{ documentId: string }>();
  const router = useRouter();
  const documentId = params?.documentId;
  if (!documentId) return null;
  return (
    <div className="flex flex-col gap-2 h-[calc(100vh-100px)] min-h-0">
      <button
        type="button"
        onClick={() => router.push("/analiza/don")}
        className="text-sm text-muted hover:text-ink self-start transition"
      >
        ← Natrag na popis
      </button>
      <DonAnalysisView documentId={documentId} containerHeightClass="flex-1" />
    </div>
  );
}
