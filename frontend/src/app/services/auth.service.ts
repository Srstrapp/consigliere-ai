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
    () => this.profile()?.nombre ?? this.user()?.email?.split('@')[0] ?? 'Usuario',
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
    // Buscar en public.users (donde se vinculan por auth_user_id)
    const { data: userRecord, error } = await this.sb.client
      .from('users')
      .select('id, nombre, email, auth_user_id')
      .eq('auth_user_id', userId)
      .maybeSingle();

    if (userRecord?.nombre) {
      this.profile.set({
        id: userId,
        email: userRecord.email ?? '',
        nombre: userRecord.nombre,
        rol: 'usuario',
      });
      return;
    }

    // Fallback: Si no hay registro en la tabla users todavía (ej: registro en proceso) 
    // usamos metadatos de Supabase Auth
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

  async signUp(
    email: string,
    password: string,
    nombre: string,
    telegramId?: string,
  ): Promise<void> {
    // 1. Registro en Supabase Auth
    const { data, error } = await this.sb.client.auth.signUp({
      email,
      password,
      options: {
        data: {
          full_name: nombre,
          telegram_id: telegramId,
        },
      },
    });
    if (error) throw error;

    if (data.user) {
      console.log('✅ Auth completada. Creando perfil en public.users...');
      
      // 2. Insert manual en la tabla de negocio (public.users)
      // Usamos upsert por si el trigger existiera y ya lo hubiera creado
      const { error: dbError } = await this.sb.client
        .from('users')
        .upsert({
          auth_user_id: data.user.id,
          email: email,
          nombre: nombre,
          telegram_id: telegramId ? parseInt(telegramId) : null,
          presupuesto_mensual: 1000 // Default inicial
        }, {
          onConflict: 'auth_user_id'
        });

      if (dbError) {
        console.error('⚠️ Error al crear perfil manual:', dbError);
        // No lanzamos error para no bloquear el login si el auth fue exitoso
      } else {
        console.log('✅ Perfil creado exitosamente en public.users');
      }
    }
  }

  async signOut(): Promise<void> {
    await this.sb.client.auth.signOut();
  }

  /** Para login desde magic link del bot: establece sesión con tokens ya validados */
  async setSessionFromToken(accessToken: string, refreshToken: string): Promise<void> {
    await this.sb.client.auth.setSession({
      access_token: accessToken,
      refresh_token: refreshToken,
    });
  }
}
