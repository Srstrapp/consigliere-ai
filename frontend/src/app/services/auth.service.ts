import { Injectable, inject, signal, computed } from '@angular/core';
import { Router } from '@angular/router';
import { Session, User } from '@supabase/supabase-js';
import { SupabaseService } from './supabase.service';

export interface UserProfile {
  id: string;
  email: string;
  nombre: string;
  rol: string;
  tenant_id?: string;
  activo?: boolean;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly sb = inject(SupabaseService);
  private readonly router = inject(Router);

  readonly session = signal<Session | null>(null);
  readonly user = signal<User | null>(null);
  readonly profile = signal<UserProfile | null>(null);
  readonly loading = signal<boolean>(true);

  readonly isAuthenticated = computed(() => !!this.session());
  readonly displayName = computed(
    () => this.profile()?.nombre ?? this.user()?.email?.split('@')[0] ?? 'Usuario'
  );
  readonly initials = computed(() => {
    const name = this.profile()?.nombre ?? this.user()?.email ?? '?';
    return name
      .split(' ')
      .map((n: string) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  });

  constructor() {
    this.init();
  }

  private async init(): Promise<void> {
    const {
      data: { session },
    } = await this.sb.client.auth.getSession();

    this.session.set(session);
    this.user.set(session?.user ?? null);

    if (session?.user) {
      await this.loadProfile(session.user.id);
    }

    this.loading.set(false);

    this.sb.client.auth.onAuthStateChange(async (event, session) => {
      this.session.set(session);
      this.user.set(session?.user ?? null);

      if (session?.user) {
        await this.loadProfile(session.user.id);
      } else {
        this.profile.set(null);
      }

      if (event === 'SIGNED_IN') {
        this.router.navigate(['/dashboard']);
      }
      if (event === 'SIGNED_OUT') {
        this.router.navigate(['/login']);
      }
    });
  }

  private async loadProfile(userId: string): Promise<void> {
    // Buscamos primero en public.usuarios (admins/ERP)
    const { data: adminProfile } = await this.sb.client
      .from('usuarios')
      .select('*')
      .eq('id', userId)
      .single();

    if (adminProfile?.nombre) {
      this.profile.set(adminProfile);
      return;
    }

    // Fallback: buscar en public.users (usuarios del bot vinculados por auth_user_id)
    const { data: botUser } = await this.sb.client
      .from('users')
      .select('id, nombre, email, presupuesto_mensual')
      .eq('auth_user_id', userId)
      .single();

    if (botUser?.nombre) {
      this.profile.set({
        id: userId,
        email: botUser.email ?? '',
        nombre: botUser.nombre,
        rol: 'usuario',
      });
      return;
    }

    // Si hay session, usar el displayName del metadata de Supabase Auth como fallback
    const user = this.user();
    const metaNombre = user?.user_metadata?.['full_name'] ?? user?.user_metadata?.['name'];
    if (metaNombre) {
      this.profile.set({
        id: userId,
        email: user?.email ?? '',
        nombre: metaNombre,
        rol: 'usuario',
      });
    } else {
      this.profile.set(null);
    }
  }

  async signIn(email: string, password: string): Promise<void> {
    const { error } = await this.sb.client.auth.signInWithPassword({ email, password });
    if (error) throw error;
  }

  async signUp(email: string, password: string, nombre: string): Promise<void> {
    const { data, error } = await this.sb.client.auth.signUp({ email, password });
    if (error) throw error;

    if (data.user) {
      await this.sb.client.from('usuarios').insert({
        id: data.user.id,
        email,
        nombre,
        rol: 'usuario',
      });
    }
  }

  async signOut(): Promise<void> {
    await this.sb.client.auth.signOut();
  }

  /** Para login desde magic link del bot: establece sesión con tokens ya validados */
  async setSessionFromToken(accessToken: string, refreshToken: string): Promise<void> {
    await this.sb.client.auth.setSession({ access_token: accessToken, refresh_token: refreshToken });
  }
}
