import { Component, OnInit } from '@angular/core';
import { LoginService, LoginState } from '../login.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-splashscreen',
  templateUrl: './splashscreen.component.html',
  styleUrls: ['./splashscreen.component.scss'],
})
export class SplashscreenComponent implements OnInit {
  constructor(private loginService: LoginService, private router: Router) {}

  ngOnInit(): void {
    if (this.loginService.getLoginState() !== LoginState.LoggedIn) {
      this.router.navigate(['/login']);
    }
    if (this.loginService.getLoginState() === LoginState.LoggedIn) {
      this.router.navigate(['/main']);
    }
  }
}
