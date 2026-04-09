import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { LucideAngularModule, Brain, Eye, EyeOff, Mail, Lock, User, ArrowRight, Loader } from 'lucide-angular';
import { AuthService } from '../../services/auth.service';

type AuthMode = 'login' | 'register';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideAngularModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css',
})
export class LoginComponent implements OnInit {
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  // Icons
  readonly Brain = Brain;
  readonly Eye = Eye;
  readonly EyeOff = EyeOff;
  readonly Mail = Mail;
  readonly Lock = Lock;
  readonly User = User;
  readonly ArrowRight = ArrowRight;
  readonly Loader = Loader;

  // State
  mode = signal<AuthMode>('login');
  loading = signal(false);
  error = signal('');
  showPassword = signal(false);

  // Form fields
  email = '';
  password = '';
  nombre = '';

  // Telegram token from URL
  telegramToken = '';
  telegramId = '';

  async ngOnInit() {
    // Obtener el token de Telegram de la URL
    this.telegramToken = this.route.snapshot.queryParamMap.get('token') || '';
    
    // Si hay token, resolvemos el ID de una vez para tenerlo listo
    if (this.telegramToken) {
      this.telegramId = await this.getTelegramIdFromToken();
    }
  }

  get isLogin(): boolean {
    return this.mode() === 'login';
  }

  toggleMode(): void {
    this.mode.set(this.isLogin ? 'register' : 'login');
    this.error.set('');
  }

  togglePassword(): void {
    this.showPassword.update((v) => !v);
  }

  private async getTelegramIdFromToken(): Promise<string> {
    if (!this.telegramToken) return '';
    
    try {
      this.loading.set(true);
      console.log('🔍 Validando token de Telegram:', this.telegramToken);
      const { environment } = await import('../../../environments/environment');
      
      // Forzamos el uso de la URL absoluta del environment
      const url = `${environment.apiUrl}/auth/token?token=${this.telegramToken}`;
      console.log('📡 Llamando a:', url);

      const res = await fetch(url);
      
      if (!res.ok) {
        const errText = await res.text();
        console.error('❌ Error en respuesta del servidor:', errText);
        this.error.set(`Error de validación: ${res.status}. El link puede haber expirado.`);
        return '';
      }

      const data = await res.json();
      console.log('📦 Respuesta de validación de token:', data);
      
      if (data.success) {
        console.log('✅ Token validado para Telegram ID:', data.telegram_id);
        return data.telegram_id.toString();
      } else {
        this.error.set('El token de Telegram no es válido. Pedí uno nuevo.');
      }
    } catch (e) {
      console.error('❌ Error de red al validar token:', e);
      this.error.set('No se pudo conectar con el servidor para validar el token.');
    } finally {
      this.loading.set(false);
    }
    return '';
  }

  private async linkTelegramAccount() {
    if (!this.telegramId) return;
    
    try {
      const session = this.auth.session();
      if (!session) return;

      const { environment } = await import('../../../environments/environment');
      await fetch(`${environment.apiUrl}/auth/link-telegram`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({ telegram_id: this.telegramId }),
      });
      console.log('✅ Vinculación de Telegram completada exitosamente');
    } catch (e) {
      console.error('❌ Error vinculando telegram:', e);
    }
  }

  async submit(): Promise<void> {
    if (!this.email || !this.password) {
      this.error.set('Completá todos los campos');
      return;
    }

    if (!this.isLogin && !this.nombre) {
      this.error.set('Ingresá tu nombre completo');
      return;
    }

    this.loading.set(true);
    this.error.set('');

    try {
      // Asegurarnos de tener el telegramId resuelto antes de proceder
      if (this.telegramToken && !this.telegramId) {
        this.telegramId = await this.getTelegramIdFromToken();
      }

      console.log('🚀 Iniciando registro:', { 
        email: this.email, 
        nombre: this.nombre, 
        telegramId: this.telegramId 
      });

      if (this.isLogin) {
        await this.auth.signIn(this.email, this.password);
        // Si no se vinculó en el registro, intentamos vincular ahora
        if (this.telegramId) {
          await this.linkTelegramAccount();
        }
        this.router.navigate(['/dashboard']);
      } else {
        await this.auth.signUp(this.email, this.password, this.nombre, this.telegramId);
        
        // El vínculo se hará automáticamente en el servidor vía metadatos + trigger
        this.mode.set('login');
        this.error.set('✅ Registro exitoso. Iniciá sesión para activar el vínculo.');
      }
    } catch (err: any) {
      const msg = err?.message ?? 'Error desconocido';
      if (msg.includes('Invalid login credentials')) {
        this.error.set('Email o contraseña incorrectos');
      } else if (msg.includes('User already registered')) {
        this.error.set('Ya existe una cuenta con ese email');
      } else if (msg.includes('Password')) {
        this.error.set('La contraseña debe tener al menos 6 caracteres');
      } else {
        this.error.set(msg);
      }
    } finally {
      this.loading.set(false);
    }
  }
}
