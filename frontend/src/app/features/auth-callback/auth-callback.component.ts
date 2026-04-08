import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-auth-callback',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="min-h-screen bg-gradient-to-br from-slate-950 via-indigo-950/30 to-slate-950
                flex items-center justify-center p-6">
      <div class="text-center max-w-sm">
        @if (loading()) {
          <div class="mb-6">
            <div class="w-16 h-16 rounded-2xl bg-indigo-500/20 border border-indigo-500/30
                        flex items-center justify-center mx-auto mb-4 animate-pulse">
              <span class="text-3xl">🔐</span>
            </div>
            <h2 class="text-xl font-semibold text-white mb-2">Verificando acceso...</h2>
            <p class="text-slate-400 text-sm">Validando tu link de Telegram</p>
          </div>
          <div class="flex justify-center gap-1">
            <div class="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
            <div class="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
            <div class="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
          </div>
        }

        @if (error()) {
          <div class="mb-6">
            <div class="w-16 h-16 rounded-2xl bg-red-500/20 border border-red-500/30
                        flex items-center justify-center mx-auto mb-4">
              <span class="text-3xl">❌</span>
            </div>
            <h2 class="text-xl font-semibold text-white mb-2">Link inválido o expirado</h2>
            <p class="text-slate-400 text-sm mb-6">{{ error() }}</p>
            <button (click)="goToLogin()"
                    class="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold
                           px-6 py-3 rounded-xl transition-colors">
              Ir al login
            </button>
          </div>
        }

        @if (success()) {
          <div>
            <div class="w-16 h-16 rounded-2xl bg-green-500/20 border border-green-500/30
                        flex items-center justify-center mx-auto mb-4">
              <span class="text-3xl">✅</span>
            </div>
            <h2 class="text-xl font-semibold text-white mb-2">¡Bienvenido, {{ userName() }}!</h2>
            <p class="text-slate-400 text-sm">Redirigiendo al dashboard...</p>
          </div>
        }
      </div>
    </div>
  `,
})
export class AuthCallbackComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private authService = inject(AuthService);

  loading = signal(true);
  error = signal<string | null>(null);
  success = signal(false);
  userName = signal('');

  async ngOnInit() {
    const token = this.route.snapshot.queryParamMap.get('token');

    if (!token) {
      this.loading.set(false);
      this.error.set('No se encontró el token de acceso. Pedí un nuevo link desde el bot.');
      return;
    }

    try {
      // Llamar al backend para validar el token
      const res = await fetch(`/api/auth/token?token=${token}`);
      const data = await res.json();

      if (!res.ok || !data.success) {
        throw new Error(data.detail || 'Token inválido o expirado');
      }

      // Si el backend nos da un magic link de Supabase Auth, usarlo
      if (data.access_token) {
        await this.authService.setSessionFromToken(data.access_token, data.refresh_token);
      }

      this.userName.set(data.nombre || 'Usuario');
      this.loading.set(false);
      this.success.set(true);

      // Redirigir al dashboard después de 1.5s
      setTimeout(() => this.router.navigate(['/dashboard']), 1500);
    } catch (err: any) {
      this.loading.set(false);
      this.error.set(err.message || 'Ocurrió un error al validar el acceso.');
    }
  }

  goToLogin() {
    this.router.navigate(['/login']);
  }
}
