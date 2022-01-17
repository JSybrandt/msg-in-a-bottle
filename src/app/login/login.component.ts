import { Component, OnInit } from '@angular/core';
import { LoginService, LoginState } from '../login.service';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { kOkStatus } from '../constants';
import { Router } from '@angular/router';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss'],
})
export class LoginComponent implements OnInit {
  email: string = '';
  waiting: boolean = false;
  secret_key: string = '';

  constructor(private loginService: LoginService, private router: Router) {}

  ngOnInit(): void {
    if (this.loginService.getLoginState() === LoginState.LoggedIn) {
      this.onLoginFinished();
    }
  }

  isNotLoggedIn(): boolean {
    return this.loginService.getLoginState() === LoginState.NotLoggedIn;
  }
  isPendingLogin(): boolean {
    return this.loginService.getLoginState() === LoginState.LoginPending;
  }
  isLoggedIn(): boolean {
    return this.loginService.getLoginState() === LoginState.LoggedIn;
  }

  submit(): void {
    this.waiting = true;
    if (this.isNotLoggedIn()) {
      this.loginService.startLogin(this.email).subscribe((status) => {
        this.waiting = false;
        if (status !== kOkStatus) {
          alert(status);
        }
      });
    }
    if (this.isPendingLogin()) {
      this.loginService.finishLogin(this.secret_key).subscribe((status) => {
        this.waiting = false;
        if (status === kOkStatus) {
          this.onLoginFinished();
        } else {
          alert(status);
        }
      });
    }
  }

  cancelLogin(): void {
    this.loginService.logout();
  }

  private onLoginFinished() {
    this.router.navigate(['/']);
  }
}
