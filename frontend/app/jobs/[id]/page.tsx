import { JobView } from "./JobView";

export default function JobPage({ params }: { params: { id: string } }) {
  return <JobView jobId={params.id} />;
}
