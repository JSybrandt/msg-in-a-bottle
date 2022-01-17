import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { LoginComponent } from './login/login.component';
import { SplashscreenComponent } from './splashscreen/splashscreen.component';
import { MainscreenComponent } from './mainscreen/mainscreen.component';

const routes: Routes = [
  { path: '', component: SplashscreenComponent },
  { path: 'login', component: LoginComponent },
  { path: 'main', component: MainscreenComponent },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule],
})
export class AppRoutingModule {}
