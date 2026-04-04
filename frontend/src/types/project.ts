/** バックエンド ProjectResponse に対応 */
export interface Project {
  id: string;
  user_id: string;
  name: string;
  channel_id: string | null;
  channel_url: string | null;
  genre: string | null;
  target_audience: string | null;
  concept: string | null;
  center_pin: string | null;
  settings: Record<string, unknown>;
  benchmark_channels: string[] | null;
  strengths: string | null;
  content_style: string | null;
  onboarding_completed: boolean;
  created_at: string;
  updated_at: string;
}
