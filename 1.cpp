#include<bits/stdc++.h>
using namespace std;
bool check(int num){
     int position =1;
    while(num>0){
       if(num%10%2==0)
          return false;
        else{
            num/=10;
            position++;
        }

}
}
int main(){
    int n;
    cin >> n;
    int cnt =0;
    for(int i=1;i<=n;i++){
        if(check(i)){
            cnt++;
        }
    }
    cout << cnt;
}

//逻辑混乱：当 i 的值被修改后，外层循环的行为变得不可预测，可能导致跳过某些数字或无限循环。

