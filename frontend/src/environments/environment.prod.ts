export const environment = {
  production: true,
  apiUrl: process.env['API_URL'] || 'https://tu-backend.railway.app/api',
  supabase: {
    url: 'https://xbcnbuioiugnlkwkvrzi.supabase.co',
    anonKey:
      'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhiY25idWlvaXVnbmxrd2t2cnppIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU1MzkzNTQsImV4cCI6MjA5MTExNTM1NH0.kheL27DH7g4cckIa1xzj1ooi9UfhnGthD358Sx1kArU',
  },
};
