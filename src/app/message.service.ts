import { Injectable } from '@angular/core';
import { kBackendRootUrl, kOkStatus } from './constants';
import { catchError, map, tap } from 'rxjs/operators';
import { Observable, of } from 'rxjs';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { LoginService, LoginState } from './login.service';

export interface MessageOverview {
  status: string;
  username?: string;
  authored_message_ids?: number[];
  may_append_message_ids?: number[];
}

@Injectable({
  providedIn: 'root',
})
export class MessageService {
  private baseUrl: string = `${kBackendRootUrl}`;
  private httpOptions = {
    headers: new HttpHeaders({ 'Content-Type': 'application/json' }),
  };

  constructor(private http: HttpClient, private loginService: LoginService) {}

  getOverview(): Observable<MessageOverview> {
    if (this.loginService.getLoginState() !== LoginState.LoggedIn) {
      throw new Error("Cannot get overview if we're not logged in.");
    }
    return this.http
      .post<MessageOverview>(
        `${this.baseUrl}`,
        { token: this.loginService.getToken() },
        this.httpOptions
      )
      .pipe(catchError(this.handleError));
  }

  private handleError(response: any): Observable<MessageOverview> {
    console.log(response.message);
    return of(response.error);
  }
}
