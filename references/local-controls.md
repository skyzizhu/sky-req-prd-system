# 页面状态与轻量控件交互

生成原型时使用：Tab承载页面状态，当前画面内的控件只做展开、选择、输入及必要联动。保持最小交互，不串起提交、取消、请求重试或结果模拟。

## 状态不能遗漏

先从方案、规则和异常恢复逐项核对实际适用的维度，再决定哪些页面画面进入states[]。例如初始、必填未填/格式错误、空数据、加载中/加载失败、提交中/成功/失败/未知、取消确认/处理中/结果、权限/只读。相同组件且恢复方式一致的错误可用代表画面与字段规则覆盖；提示位置、必要元素或恢复方式不同的不能一并删掉。不适用说明理由，不机械填一套十二状态。

单选切换到线上、打开辅助需求、下拉展开等属于局部操作，不再为每一步造Tab。数据为空、加载失败、业务拒绝等不能因为涉及下拉就当作“仅展开”删掉。只读/禁用、取消与失败等页面状态仍由Tab直接查看，不要求按一串交互才能到达。

在page.state_review登记覆盖核对，规则正文继续只放rule_details。登记可以随项目增量修订，不要求旧案例自动重写：

```json
[
  {"dimension":"初始进入","status":"covered","state_ids":["default"]},
  {"dimension":"字段校验","status":"covered","state_ids":["invalid"]},
  {"dimension":"场次选项与参加方式联动","status":"local","selectors":["#default-session","#default-method"],"reason":"展开场次；切线上看邮箱，再切现场核对清空"},
  {"dimension":"取消","status":"not_applicable","reason":"本页面不承担取消，取消状态在本人记录页"}
]
```

结构检查只验证登记的页面状态/控件引用有效，不能证明需求语义已穷尽。每个新页面都应登记本次适用维度并实际操作核对，避免将页面状态漏登记或把局部变化塞回Tab。

## 仅声明必要交互

共享运行时只放行显式声明的原生控件，不为局部交互另写业务脚本。`data-prototype-mode="static"`仍表示预设页面状态阅读器；`interaction.action="inspect"`只表示标注关联。

| data-ps-local | 元素或组 | 能做什么 |
| --- | --- | --- |
| select | select | 展开并选择，遵守原生禁用项 |
| choice | 单选/复选/开关自身或所在组 | 改变选中值，互斥和禁用按原生属性 |
| input | 普通文本/邮箱/数字/日期/时间/滑块等或textarea | 本地改值，不模拟提交校验与保存 |
| disclosure | details | 原生summary展开/收起 |

不支持文件上传、真实提交、保存、跳转、接口、存储、通知、定时进度。普通业务按钮和链接保留产品外观，但点击不执行操作；错误、取消与提交结果从Tab查看。实际产品disabled/readonly继续如实呈现，不能为演示解除。

```html
<select id="default-session" data-rule-ref="INT-SESSION" data-ps-local="select">
  <option value="s1" selected>11月5日 · 余量8</option>
  <option value="s2" disabled>11月6日 · 已满额</option>
</select>
<div id="default-method" data-rule-ref="INT-METHOD"
     class="sr-control-group" data-ps-local="choice" data-ps-key="method">
  <label><input id="default-onsite" data-rule-ref="INT-METHOD" type="radio" name="default-method" value="onsite" checked>现场</label>
  <label><input id="default-online" data-rule-ref="INT-METHOD" type="radio" name="default-method" value="online">线上</label>
</div>
<div data-ps-when-key="method" data-ps-when-value="online" data-ps-clear-hidden hidden>
  <label for="default-email">接收邮箱</label>
  <input id="default-email" type="email" data-rule-ref="INT-EMAIL" data-ps-local="input">
</div>
```

每个原生控件有唯一id及data-rule-ref；同组子选项可引用同一interaction，标注仍定位组容器，不给每个选项重复正文。条件值来自同画面内data-ps-key元素：select/input使用value，单选组使用已选value，复选或开关使用字符串true/false。依赖只在本画面解析，避免跨状态重名radio相互影响。

`data-ps-when-key`与`data-ps-when-value`控制显隐；仅在产品规则要求隐藏时清空，才加`data-ps-clear-hidden`。初始值、联动结果和规则必须一致。单个条件足够时不做复杂表达式或多步骤演示。

实际规则有多选上限时，可在choice组加`data-ps-max="2" data-ps-feedback="default-limit"`，并在原位提供`id="default-limit" data-ps-local-error hidden`的既定错误文案。超限尝试回退本次勾选并展示提示；合法变更收起提示。上限和文案从规则生成，不另维护一份业务决策。没有该限制就不加。

## 控件与标注互不触发

- 点击/键盘操作控件只改变局部值，不切右侧标注、不切Tab；点击编号只定位规则，不选择单选、不勾选复选、不展开下拉。禁止给整个控件或label绑定“点击看规则”。
- 共享运行时给标注目标预留独立编号栏，蓝色框只表示正在阅读该控件，不改变checked/selected。复杂表格单元格、summary等需要在源布局中预留独立编号栏，不能把编号盖在控件上。
- 联动隐藏某个当前标注目标时，其编号同步隐藏，右侧保留正在阅读的规则；再次出现恢复定位。不因为用户操作控件便抢规则面板焦点。
- 切换Tab或重新打开状态链接恢复该画面的预设值、展开情况及局部提示；不同状态不共享试填草稿。状态对照保留各自画面，控件只影响所在画面。

## 实际检查

1. 对照方案和规则核对Tab状态是否完整，逐一打开异常和边界画面；仅有状态名或规则引用不算对应UI已交付。
2. 实际展开下拉、切单选、勾选复选、开关显隐/清空；核对选项、默认和限制。不要把局部核对做成新Tab。
3. 点击控件前后，右侧当前标注和hash不变；点击编号前后，控件值与展开情况不变。检查编号与实际可点击控件的矩形区域不重叠，包含窄屏与键盘路径。
4. 单状态、状态对照、独立页、站点iframe、切Tab重置均验证；确认提交/链接/表单Enter不发真实请求或跳转。
5. 页面预设状态的elements记录本状态默认必须可见的元素；局部才出现的元素在state_review.local核对路径引用，不冒充默认可见。实际浏览器补验联动后的元素和标注可见性；需要条件UI验收的规则不能只有文字而没有实际可查看路径。
