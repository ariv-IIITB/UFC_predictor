import { createClient } from '@supabase/supabase-js'

export function createServerClient() {
  console.log('SUPABASE_URL:', process.env.NEXT_PUBLIC_SUPABASE_URL)
  console.log('KEY LENGTH:', process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.length, 'SEGMENTS:', process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.split('.').length)
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { auth: { persistSession: false } }
  )
}
