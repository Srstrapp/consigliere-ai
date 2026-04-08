import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class DataService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getUsuario(telegramId: number): Observable<any> {
    return this.http.get(`${this.apiUrl}/usuario/${telegramId}`);
  }

  getGastos(telegramId: number): Observable<any> {
    return this.http.get(`${this.apiUrl}/${telegramId}/gastos`);
  }

  getMetas(telegramId: number): Observable<any> {
    return this.http.get(`${this.apiUrl}/${telegramId}/metas`);
  }

  getResumenGastos(telegramId: number): Observable<any> {
    return this.http.get(`${this.apiUrl}/${telegramId}/gastos/resumen`);
  }
}
