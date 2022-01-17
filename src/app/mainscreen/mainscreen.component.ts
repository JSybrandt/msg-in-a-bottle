import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { LoginService, LoginState } from '../login.service';

@Component({
  selector: 'app-mainscreen',
  templateUrl: './mainscreen.component.html',
  styleUrls: ['./mainscreen.component.scss'],
})
export class MainscreenComponent implements OnInit {
  constructor(private loginService: LoginService, private router: Router) {}

  ngOnInit(): void {
    if (this.loginService.getLoginState() !== LoginState.LoggedIn) {
      this.router.navigate(['/']);
    }
  }
}
