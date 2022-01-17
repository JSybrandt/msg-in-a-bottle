import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { kBackendRootUrl, kOkStatus } from './constants';
import { Observable, of } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';

export enum LoginState {
  // We have nothing from the user.
  NotLoggedIn,
  // We know the user's email and are waiting on the secret key.
  LoginPending,
  // We have the user's token.
  LoggedIn,
}

interface LoginResponse {
  status: string;
  token?: string;
}

@Injectable({
  providedIn: 'root',
})
export class LoginService {
  // Set after login started.
  private email?: string;
  private token?: string;

  private loginUrl: string = `${kBackendRootUrl}/login`;
  private httpOptions = {
    headers: new HttpHeaders({ 'Content-Type': 'application/json' }),
  };

  constructor(private http: HttpClient) {}

  getLoginState(): LoginState {
    if (this.token !== undefined) {
      return LoginState.LoggedIn;
    }
    if (this.email !== undefined) {
      return LoginState.LoginPending;
    }
    return LoginState.NotLoggedIn;
  }

  // Returns the status of the login message.
  startLogin(email: string): Observable<string> {
    if (this.getLoginState() !== LoginState.NotLoggedIn) {
      throw new Error('startLogin called twice.');
    }
    return this.http
      .post<LoginResponse>(this.loginUrl, { email: email }, this.httpOptions)
      .pipe(
        catchError(this.handleError),
        map((response, _) => {
          if (response.status === kOkStatus) {
            this.email = email;
          }
          return response.status;
        })
      );
  }

  finishLogin(secret_key: string): Observable<string> {
    if (this.getLoginState() !== LoginState.LoginPending) {
      throw new Error('finishLogin called before startLogin.');
    }
    return this.http
      .post<LoginResponse>(
        this.loginUrl,
        { email: this.email, secret_key: secret_key },
        this.httpOptions
      )
      .pipe(
        catchError(this.handleError),
        map((response, _) => {
          if (response.status === kOkStatus) {
            this.token = response.token;
          }
          return response.status;
        })
      );
  }

  logout(): void {
    this.email = undefined;
    this.token = undefined;
  }

  getEmail(): string | undefined {
    return this.email;
  }

  getToken(): string | undefined {
    return this.token;
  }

  private handleError(response: any): Observable<LoginResponse> {
    console.log(response.message);
    return of({ status: response.error.status });
  }
}
