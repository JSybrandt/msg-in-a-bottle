import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { LoginService, LoginState } from '../login.service';
import { MessageService, MessageOverview } from '../message.service';
import { kOkStatus } from '../constants';

@Component({
  selector: 'app-mainscreen',
  templateUrl: './mainscreen.component.html',
  styleUrls: ['./mainscreen.component.scss'],
})
export class MainscreenComponent implements OnInit {
  constructor(
    private loginService: LoginService,
    private messageService: MessageService,
    private router: Router
  ) {}

  ngOnInit(): void {
    if (this.loginService.getLoginState() === LoginState.LoggedIn) {
      this.messageService.getOverview().subscribe((mo: MessageOverview) => {
        if (mo.status === kOkStatus) {
          this.renderOverview(mo);
        } else {
          this.bounceBackToRoot();
        }
      });
    } else {
      this.bounceBackToRoot();
    }
  }

  renderOverview(messageOverview: MessageOverview): void {
    if (messageOverview.status !== kOkStatus) {
      alert(messageOverview.status);
      this.bounceBackToRoot();
    }
  }

  bounceBackToRoot(): void {
    this.loginService.logout();
    this.router.navigate(['/']);
  }
}
