import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

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
export class LoginComponent {
  private readonly auth = inject(AuthService);

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
      if (this.isLogin) {
        await this.auth.signIn(this.email, this.password);
      } else {
        await this.auth.signUp(this.email, this.password, this.nombre);
        this.error.set('');
        this.mode.set('login');
        this.error.set('✅ Cuenta creada. Iniciá sesión.');
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
